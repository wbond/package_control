import datetime
import os
import threading
import time

import sublime

from .show_error import show_error
from .console_write import console_write
from .package_installer import PackageInstaller
from .package_renamer import PackageRenamer
from .settings import pc_settings_filename, load_list_setting


class AutomaticUpgrader(threading.Thread):

    """
    Automatically checks for updated packages and installs them. controlled
    by the `auto_upgrade`, `auto_upgrade_ignore`, and `auto_upgrade_frequency`
    settings.
    """

    def __init__(self, found_packages, found_dependencies):
        """
        :param found_packages:
            A list of package names for the packages that were found to be
            installed on the machine.

        :param found_dependencies:
            A list of installed dependencies found on the machine
        """

        self.installer = PackageInstaller()
        self.manager = self.installer.manager

        self.package_renamer = PackageRenamer()
        self.package_renamer.load_settings()

        # Detect if a package is missing that should be installed
        self.settings = sublime.load_settings(pc_settings_filename())
        self.installed_packages = load_list_setting(self.settings, 'installed_packages')
        self.missing_packages = list(set(self.installed_packages) - set(found_packages))
        self.missing_dependencies = list(
            set(self.manager.find_required_dependencies()) - set(found_dependencies))
        threading.Thread.__init__(self)

    def run(self):
        num_installed = self.install_missing_dependencies()
        if num_installed > 0:
            # As installing dependencies asks to restart ST, further
            # install/upgrade operations might most likely be interrupted
            # anyway and therefore are skipped. The last-run is not saved to
            # restart auto upgrader after restarting ST immediatelly.
            return

        self.install_missing_packages()
        self.upgrade_packages()

    def install_missing_dependencies(self):
        """
        Installs all dependencies that were listed in the list of
        `installed_packages` from Package Control.sublime-settings but were not
        found on the filesystem and passed as `found_dependencies`.
        """

        # We always install missing dependencies - this operation does not
        # obey the "install_missing" setting since not installing dependencies
        # would result in broken packages.
        if not self.missing_dependencies:
            return 0

        num_missing = len(self.missing_dependencies)
        dependency_s = 'ies' if num_missing != 1 else 'y'
        console_write('Installing %s missing dependenc%s', (num_missing, dependency_s))

        num_installed = 0
        for dependency in self.missing_dependencies:
            if self.manager.install_package(dependency, is_dependency=True):
                console_write('Installed missing dependency %s', dependency)
                num_installed += 1

        if num_installed:
            def notify_restart():
                dependency_was = 'ies were' if num_installed != 1 else 'y was'
                show_error(
                    '''
                    %s missing dependenc%s just installed. Sublime Text
                    should be restarted, otherwise one or more of the
                    installed packages may not function properly.
                    ''',
                    (num_installed, dependency_was)
                )
            sublime.set_timeout(notify_restart, 1000)

        return num_installed

    def install_missing_packages(self):
        """
        Installs all packages that were listed in the list of
        `installed_packages` from Package Control.sublime-settings but were not
        found on the filesystem and passed as `found_packages`.
        """

        # Missing package installs are controlled by a setting
        if not self.missing_packages or not self.settings.get('install_missing'):
            return

        num_missing = len(self.missing_packages)

        package_s = 's' if num_missing > 1 else ''
        console_write('Installing %s missing package%s', (num_missing, package_s))

        # Fetching the list of packages also grabs the renamed packages
        self.manager.list_available_packages()
        renamed_packages = self.manager.settings.get('renamed_packages', {})

        disabled_packages = self.installer.disable_packages(self.missing_packages, 'install')

        time.sleep(0.7)

        for package in self.missing_packages:

            # If the package has been renamed, detect the rename and update
            # the settings file with the new name as we install it
            if package in renamed_packages:
                old_name = package
                new_name = renamed_packages[old_name]

                self.installed_packages.remove(old_name)
                self.installed_packages.append(new_name)
                self.settings.set('installed_packages', self.installed_packages)
                sublime.save_settings(pc_settings_filename())
                # remove the old package from list of disabled packages
                if package in disabled_packages:
                    self.installer.reenable_package(package, 'remove')

                package = new_name

            if self.manager.install_package(package):
                if package in disabled_packages:
                    self.installer.reenable_package(package, 'install')

                console_write('Installed missing package %s', package)

    def upgrade_packages(self):
        """
        Upgrades all packages that are not currently upgraded to the lastest
        version. Also renames any installed packages to their new names.
        """

        if not self.settings.get('auto_upgrade'):
            return

        cookie = LastRunCookie(self.settings.get('auto_upgrade_frequency'))
        if not cookie.elapsed():
            last_run = datetime.datetime.fromtimestamp(cookie.last_run)
            next_run = datetime.datetime.fromtimestamp(cookie.next_run)
            date_format = '%Y-%m-%d %H:%M:%S'
            console_write(
                '''
                Skipping automatic upgrade, last run at %s, next run at %s or after
                ''',
                (last_run.strftime(date_format), next_run.strftime(date_format))
            )
            return

        self.package_renamer.rename_packages(self.installer)

        # Create a list of package names to upgrade
        packages = [
            p[0] for p in self.installer.make_package_list(
                ['install', 'reinstall', 'downgrade', 'overwrite', 'none'],
                ignore_packages=self.settings.get('auto_upgrade_ignore')
            )
        ]

        # If Package Control is being upgraded, just do that and restart
        if 'Package Control' in packages:
            packages = ['Package Control']
        else:
            cookie.update()

        if not packages:
            console_write('No updated packages')
            return

        console_write('Installing %s upgrades', len(packages))

        disabled_packages = self.installer.disable_packages(packages, 'upgrade')

        # Wait so that the ignored packages can be "unloaded"
        time.sleep(0.7)

        for package in packages:
            if self.manager.install_package(package):
                if package in disabled_packages:
                    self.installer.reenable_package(package, 'upgrade')
                version = self.manager.get_version(package)
                console_write('Upgraded %s to %s', (package, version))


class LastRunCookie(object):

    """
    A class to handle loading, checking and updating the last-run file.
    """

    def __init__(self, frequency):
        self.frequency = frequency
        self.now = None
        self.next_run = None
        self.last_run = None
        self.last_run_file = os.path.join(
            sublime.cache_path(), 'Package Control', 'last-run')
        try:
            with open(self.last_run_file) as f:
                self.last_run = int(f.read())
        except (FileNotFoundError, ValueError):
            pass

    def elapsed(self):
        """
        Check if it's time for upate.

        :returns:
            True if last update was long ago.
        """
        self.now = int(time.time())
        if self.frequency and self.last_run:
            self.next_run = int(self.last_run) + (self.frequency * 60 * 60)
        else:
            self.next_run = self.now

        return self.now >= self.next_run

    def update(self):
        """
        Update the last_run with the timestamp.
        """
        os.makedirs(os.path.dirname(self.last_run_file), mode=0o555, exist_ok=True)
        with open(self.last_run_file, 'w') as f:
            f.write(str(int(self.now)))
            self.last_run = self.now
