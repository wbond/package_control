import threading
import os
import json
import datetime
# To prevent import errors in thread with datetime
import locale  # noqa
import time

import sublime

from . import sys_path
from .show_error import show_error
from .console_write import console_write
from .package_installer import PackageInstaller
from .package_renamer import PackageRenamer
from .settings import pc_settings_filename, load_list_setting

USE_QUICK_PANEL_ITEM = hasattr(sublime, 'QuickPanelItem')


class AutomaticUpgrader(threading.Thread):

    """
    Automatically checks for updated packages and installs them. controlled
    by the `auto_upgrade`, `auto_upgrade_ignore`, and `auto_upgrade_frequency`
    settings.
    """

    def __init__(self, found_packages, found_libraries):
        """
        :param found_packages:
            A list of package names for the packages that were found to be
            installed on the machine.

        :param found_libraries:
            A list of the library.Library() objects for all installed
            libraries found on the machine
        """

        self.installer = PackageInstaller()
        self.manager = self.installer.manager

        self.load_settings()

        self.package_renamer = PackageRenamer()

        self.auto_upgrade = self.settings.get('auto_upgrade')
        self.auto_upgrade_ignore = self.settings.get('auto_upgrade_ignore')

        now = int(time.time())

        self.last_run = None
        self.last_version = 0
        self.next_run = now
        self.current_version = int(sublime.version())

        self.load_last_run()

        # Detect if a package is missing that should be installed
        self.missing_packages = list(set(self.installed_packages) - set(found_packages))
        self.missing_libraries = sorted(set(self.manager.find_required_libraries()) - set(found_libraries))

        if self.auto_upgrade and self.next_run <= now:
            self.save_last_run(now)

        threading.Thread.__init__(self)

    def load_last_run(self):
        """
        Loads the last run time from disk into memory
        """

        legacy_last_run_file = os.path.join(sys_path.packages_path, 'User', 'Package Control.last-run')
        if os.path.exists(legacy_last_run_file):
            try:
                with open(legacy_last_run_file) as fobj:
                    self.last_run = int(fobj.read())
                os.unlink(legacy_last_run_file)
            except (FileNotFoundError, ValueError):
                pass

        try:
            with open(os.path.join(sys_path.pc_cache_dir(), 'last_run.json')) as fobj:
                last_run_data = json.load(fobj)
            self.last_run = int(last_run_data['timestamp'])
            self.last_version = int(last_run_data['st_version'])
        except (FileNotFoundError, ValueError, TypeError):
            pass

        frequency = self.settings.get('auto_upgrade_frequency')
        if frequency:
            if self.last_run:
                self.next_run = int(self.last_run) + (frequency * 60 * 60)

    def save_last_run(self, last_run):
        """
        Saves a record of when the last run was

        :param last_run:
            The unix timestamp of when to record the last run as
        """

        with open(os.path.join(sys_path.pc_cache_dir(), 'last_run.json'), 'w') as fobj:
            json.dump({
                'timestamp': last_run,
                'st_version': self.current_version
            }, fp=fobj)

    def load_settings(self):
        """
        Loads the list of installed packages
        """

        self.settings = sublime.load_settings(pc_settings_filename())
        self.installed_packages = load_list_setting(self.settings, 'installed_packages')
        self.should_install_missing = self.settings.get('install_missing')

    def run(self):
        self.install_missing()

        if self.next_run > int(time.time()) and \
                self.last_version == self.current_version:
            self.print_skip()
            return

        if self.last_version != self.current_version and self.last_version != 0:
            console_write(
                '''
                Detected Sublime Text update, looking for package updates
                '''
            )

        self.upgrade_packages()

    def install_missing(self):
        """
        Installs all packages that were listed in the list of
        `installed_packages` from Package Control.sublime-settings but were not
        found on the filesystem and passed as `found_packages`. Also installs
        any missing libraries.
        """

        # We always install missing libraries - this operation does not
        # obey the "install_missing" setting since not installing libraries
        # would result in broken packages.
        if self.missing_libraries:
            total_missing_libraries = len(self.missing_libraries)
            library_s = 'ies' if total_missing_libraries != 1 else 'y'
            console_write(
                '''
                Installing %s missing librar%s
                ''',
                (total_missing_libraries, library_s)
            )

            libraries_installed = 0

            for lib in self.missing_libraries:
                if self.installer.manager.install_library(lib.name, lib.python_version):
                    console_write('Installed missing library %s for Python %s', (lib.name, lib.python_version))
                    libraries_installed += 1

            if libraries_installed:
                def notify_restart():
                    library_was = 'ies were' if libraries_installed != 1 else 'y was'
                    show_error(
                        '''
                        %s missing librar%s just installed. Sublime Text
                        should be restarted, otherwise one or more of the
                        installed packages may not function properly.
                        ''',
                        (libraries_installed, library_was)
                    )
                sublime.set_timeout(notify_restart, 1000)

        # Missing package installs are controlled by a setting
        if not self.missing_packages or not self.should_install_missing:
            return

        total_missing_packages = len(self.missing_packages)

        if total_missing_packages > 0:
            package_s = 's' if total_missing_packages != 1 else ''
            console_write(
                '''
                Installing %s missing package%s
                ''',
                (total_missing_packages, package_s)
            )

        # Fetching the list of packages also grabs the renamed packages
        self.manager.list_available_packages()
        renamed_packages = self.manager.settings.get('renamed_packages', {})

        installed_packages = []
        disabled_packages = self.installer.disable_packages(self.missing_packages, 'install')
        # Wait so that the ignored packages can be "unloaded"
        time.sleep(0.7)

        try:
            for package_name in self.missing_packages:

                # If the package has been renamed, detect the rename and update
                # the settings file with the new name as we install it
                if package_name in renamed_packages:
                    old_name = package_name
                    package_name = renamed_packages[old_name]

                    installed_packages.append(old_name)
                    self.installed_packages.remove(old_name)
                    self.installed_packages.append(package_name)
                    self.settings.set('installed_packages', self.installed_packages)
                    sublime.save_settings(pc_settings_filename())

                result = self.installer.manager.install_package(package_name)
                # upgrade not dereffered to next start
                if result is not None and package_name in disabled_packages:
                    installed_packages.append(package_name)

                if result is not False:
                    console_write(
                        '''
                        Installed missing package %s
                        ''',
                        package_name
                    )

        finally:
            if installed_packages:
                time.sleep(0.7)
                self.installer.reenable_packages(installed_packages, 'install')

    def print_skip(self):
        """
        Prints a notice in the console if the automatic upgrade is skipped
        due to already having been run in the last `auto_upgrade_frequency`
        hours.
        """

        last_run = datetime.datetime.fromtimestamp(self.last_run)
        next_run = datetime.datetime.fromtimestamp(self.next_run)
        date_format = '%Y-%m-%d %H:%M:%S'
        console_write(
            '''
            Skipping automatic upgrade, last run at %s, next run at %s or after
            ''',
            (last_run.strftime(date_format), next_run.strftime(date_format))
        )

    def upgrade_packages(self):
        """
        Upgrades all packages that are not currently upgraded to the lastest
        version. Also renames any installed packages to their new names.
        """

        if not self.auto_upgrade:
            return

        self.package_renamer.rename_packages(self.installer.manager)

        package_list = self.installer.make_package_list(
            [
                'install',
                'reinstall',
                'downgrade',
                'overwrite',
                'none'
            ],
            ignore_packages=self.auto_upgrade_ignore
        )

        if USE_QUICK_PANEL_ITEM:
            package_list = [info.trigger for info in package_list]
        else:
            package_list = [info[0] for info in package_list]

        # If Package Control is being upgraded, just do that and restart
        if 'Package Control' in package_list:
            if self.last_run:
                def reset_last_run():
                    # Re-save the last run time so it runs again after PC has
                    # been updated
                    self.save_last_run(self.last_run)
                sublime.set_timeout(reset_last_run, 1)
            package_list = ['Package Control']

        if not package_list:
            console_write(
                '''
                No updated packages
                '''
            )
            return

        console_write(
            '''
            Installing %s upgrades
            ''',
            len(package_list)
        )

        upgraded_packages = []
        disabled_packages = self.installer.disable_packages(package_list, 'upgrade')
        # Wait so that the ignored packages can be "unloaded"
        time.sleep(0.7)

        try:
            for package_name in package_list:
                result = self.installer.manager.install_package(package_name)

                # upgrade not dereffered to next start
                if result is not None and package_name in disabled_packages:
                    upgraded_packages.append(package_name)

                if result is not False:
                    version = self.installer.manager.get_version(package_name)
                    console_write(
                        '''
                        Upgraded %s to %s
                        ''',
                        (package_name, version)
                    )

        finally:
            if upgraded_packages:
                time.sleep(0.7)
                self.installer.reenable_packages(upgraded_packages, 'upgrade')
