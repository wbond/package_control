import threading
import re
import os
import datetime
import time

import sublime

from .show_error import show_error
from .console_write import console_write
from .package_installer import PackageInstaller
from .package_renamer import PackageRenamer
from .open_compat import open_compat, read_compat
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

        self.load_settings()

        self.package_renamer = PackageRenamer()
        self.package_renamer.load_settings()

        self.auto_upgrade = self.settings.get('auto_upgrade')
        self.auto_upgrade_ignore = self.settings.get('auto_upgrade_ignore')

        self.load_last_run()
        self.determine_next_run()

        # Detect if a package is missing that should be installed
        self.missing_packages = list(set(self.installed_packages) -
            set(found_packages))
        self.missing_dependencies = list(set(self.manager.find_required_dependencies()) -
            set(found_dependencies))

        if self.auto_upgrade and self.next_run <= time.time():
            self.save_last_run(time.time())

        threading.Thread.__init__(self)

    def load_last_run(self):
        """
        Loads the last run time from disk into memory
        """

        self.last_run = None

        self.last_run_file = os.path.join(sublime.packages_path(), 'User',
            'Package Control.last-run')

        if os.path.isfile(self.last_run_file):
            with open_compat(self.last_run_file) as fobj:
                try:
                    self.last_run = int(read_compat(fobj))
                except ValueError:
                    pass

    def determine_next_run(self):
        """
        Figure out when the next run should happen
        """

        self.next_run = int(time.time())

        frequency = self.settings.get('auto_upgrade_frequency')
        if frequency:
            if self.last_run:
                self.next_run = int(self.last_run) + (frequency * 60 * 60)
            else:
                self.next_run = time.time()

    def save_last_run(self, last_run):
        """
        Saves a record of when the last run was

        :param last_run:
            The unix timestamp of when to record the last run as
        """

        with open_compat(self.last_run_file, 'w') as fobj:
            fobj.write(str(int(last_run)))

    def load_settings(self):
        """
        Loads the list of installed packages
        """

        self.settings = sublime.load_settings(pc_settings_filename())
        self.installed_packages = load_list_setting(self.settings, 'installed_packages')
        self.should_install_missing = self.settings.get('install_missing')

    def run(self):
        self.install_missing()

        if self.next_run > time.time():
            self.print_skip()
            return

        self.upgrade_packages()

    def install_missing(self):
        """
        Installs all packages that were listed in the list of
        `installed_packages` from Package Control.sublime-settings but were not
        found on the filesystem and passed as `found_packages`. Also installs
        any missing dependencies.
        """

        # We always install missing dependencies - this operation does not
        # obey the "install_missing" setting since not installing dependencies
        # would result in broken packages.
        if self.missing_dependencies:
            total_missing_dependencies = len(self.missing_dependencies)
            dependency_s = 'ies' if total_missing_dependencies != 1 else 'y'
            console_write(u'Installing %s missing dependenc%s' %
                (total_missing_dependencies, dependency_s), True)

            dependencies_installed = 0

            for dependency in self.missing_dependencies:
                if self.installer.manager.install_package(dependency, is_dependency=True):
                    console_write(u'Installed missing dependency %s' % dependency, True)
                    dependencies_installed += 1

            if dependencies_installed:
                def notify_restart():
                    dependency_was = 'ies were' if dependencies_installed != 1 else 'y was'
                    message = (u'%s missing dependenc%s just ' +
                        u'installed. Sublime Text should be restarted, otherwise ' +
                        u'one or more of the installed packages may not function ' +
                        u'properly.') % (dependencies_installed, dependency_was)
                    show_error(message)
                sublime.set_timeout(notify_restart, 1000)

        # Missing package installs are controlled by a setting
        if not self.missing_packages or not self.should_install_missing:
            return

        total_missing_packages = len(self.missing_packages)

        if total_missing_packages > 0:
            package_s = 's' if total_missing_packages != 1 else ''
            console_write(u'Installing %s missing package%s' %
                (total_missing_packages, package_s), True)

        # Fetching the list of packages also grabs the renamed packages
        self.manager.list_available_packages()
        renamed_packages = self.manager.settings.get('renamed_packages', {})

        for package in self.missing_packages:

            # If the package has been renamed, detect the rename and update
            # the settings file with the new name as we install it
            if package in renamed_packages:
                old_name = package
                new_name = renamed_packages[old_name]
                def update_installed_packages():
                    self.installed_packages.remove(old_name)
                    self.installed_packages.append(new_name)
                    self.settings.set('installed_packages', self.installed_packages)
                    sublime.save_settings(pc_settings_filename())
                sublime.set_timeout(update_installed_packages, 10)
                package = new_name

            if self.installer.manager.install_package(package):
                console_write(u'Installed missing package %s' % package, True)

    def print_skip(self):
        """
        Prints a notice in the console if the automatic upgrade is skipped
        due to already having been run in the last `auto_upgrade_frequency`
        hours.
        """

        last_run = datetime.datetime.fromtimestamp(self.last_run)
        next_run = datetime.datetime.fromtimestamp(self.next_run)
        date_format = '%Y-%m-%d %H:%M:%S'
        message_string = u'Skipping automatic upgrade, last run at %s, next run at %s or after' % (
            last_run.strftime(date_format), next_run.strftime(date_format))
        console_write(message_string, True)

    def upgrade_packages(self):
        """
        Upgrades all packages that are not currently upgraded to the lastest
        version. Also renames any installed packages to their new names.
        """

        if not self.auto_upgrade:
            return

        self.package_renamer.rename_packages(self.installer)

        package_list = self.installer.make_package_list(['install',
            'reinstall', 'downgrade', 'overwrite', 'none'],
            ignore_packages=self.auto_upgrade_ignore)

        # If Package Control is being upgraded, just do that and restart
        for package in package_list:
            if package[0] != 'Package Control':
                continue

            def reset_last_run():
                # Re-save the last run time so it runs again after PC has
                # been updated
                self.save_last_run(self.last_run)
            sublime.set_timeout(reset_last_run, 1)
            package_list = [package]
            break

        if not package_list:
            console_write(u'No updated packages', True)
            return

        console_write(u'Installing %s upgrades' % len(package_list), True)

        disabled_packages = []

        def do_upgrades():
            # Wait so that the ignored packages can be "unloaded"
            time.sleep(0.7)

            # We use a function to generate the on-complete lambda because if
            # we don't, the lambda will bind to info at the current scope, and
            # thus use the last value of info from the loop
            def make_on_complete(name):
                return lambda: self.installer.reenable_package(name)

            for info in package_list:
                if info[0] in disabled_packages:
                    on_complete = make_on_complete(info[0])
                else:
                    on_complete = None

                self.installer.manager.install_package(info[0])

                version = re.sub('^.*?(v[\d\.]+).*?$', '\\1', info[2])
                if version == info[2] and version.find('pull with') != -1:
                    vcs = re.sub('^pull with (\w+).*?$', '\\1', version)
                    version = 'latest %s commit' % vcs
                message_string = u'Upgraded %s to %s' % (info[0], version)
                console_write(message_string, True)
                if on_complete:
                    sublime.set_timeout(on_complete, 700)

        # Disabling a package means changing settings, which can only be done
        # in the main thread. We then create a new background thread so that
        # the upgrade process does not block the UI.
        def disable_packages():
            packages = [info[0] for info in package_list]
            disabled_packages.extend(self.installer.disable_packages(packages, 'upgrade'))
            threading.Thread(target=do_upgrades).start()
        sublime.set_timeout(disable_packages, 1)
