import os
import threading
import time

import sublime

from . import sys_path, __version__
from .automatic_upgrader import AutomaticUpgrader
from .clear_directory import clear_directory, delete_directory
from .console_write import console_write
from .package_disabler import PackageDisabler
from .package_io import (
    create_empty_file,
    get_installed_package_path,
    package_file_exists
)
from .package_manager import PackageManager
from .package_tasks import PackageTaskRunner
from .settings import load_list_setting, pc_settings_filename, save_list_setting
from .show_error import show_error, show_message


class PackageCleanup(threading.Thread, PackageDisabler):

    """
    Perform initial package maintenance tasks after start of ST.

    It's main purpose is to remove old folders and bring packages and libraries
    to a fully working state as specified by `installed_packages` no matter
    what is found in filesystem.

    It's enough to place a Package Control.sublime-settings with desired list of
    `installed_packages` into User package. This task does the rest.

    The following tasks are performed one after another:

    1. Complete pending operations, which had been deferred due to locked files.
    2. Remove packages, which exist in filesystem but not in `installed_packages`.
    3. Migrate or upgrade incompatible packages immediately.
    4. Install packages, which don't exist in filesystem but in `installed_packages`.
    5. Install required libraries, which have not yet been installed by step 3. or 4.
    6. Removes libraries, which are no longer required by finally present packages.
    """

    def __init__(self):
        threading.Thread.__init__(self)
        PackageDisabler.__init__(self)
        self.manager = PackageManager()
        self.pc_filename = pc_settings_filename()
        self.pc_settings = sublime.load_settings(self.pc_filename)
        self.failed_cleanup = set()
        self.updated_libraries = False

    def run(self):
        # This song and dance is necessary so Package Control doesn't try to clean
        # itself up, but also get properly marked as installed in the settings
        # Ensure we record the installation of Package Control itself
        installed_packages = load_list_setting(self.pc_settings, 'installed_packages')
        if 'Package Control' not in installed_packages:
            self.manager.record_usage({
                'package': 'Package Control',
                'operation': 'install',
                'version': __version__
            })
            installed_packages.add('Package Control')
            save_list_setting(self.pc_settings, self.pc_filename, 'installed_packages', installed_packages)

        # Scan through packages and complete pending operations
        found_packages = self.cleanup_pending_packages()

        # Cleanup packages that were installed via Package Control, but have been
        # removed from the "installed_packages" list - usually by removing them
        # from another computer and the settings file being synced.
        removed_packages = self.remove_orphaned_packages(found_packages)
        found_packages -= removed_packages

        # Make sure we didn't accidentally ignore packages because something was
        # interrupted before it completed. Keep orphan packages disabled which
        # are deferred to next start.
        in_process = load_list_setting(self.pc_settings, 'in_process_packages') - removed_packages
        if in_process:
            console_write(
                'Re-enabling %d package%s after a Package Control operation was interrupted...',
                (len(in_process), 's' if len(in_process) != 1 else '')
            )
            self.reenable_packages({self.ENABLE: in_process})

        # Check metadata to verify packages were not improperly installed
        self.migrate_incompatible_packages(found_packages)

        self.install_missing_packages(found_packages)
        self.install_missing_libraries()

        if self.pc_settings.get('remove_orphaned', True):
            self.manager.cleanup_libraries()

        if self.pc_settings.get('auto_upgrade'):
            AutomaticUpgrader(self.manager).run()

        if self.failed_cleanup:
            show_error(
                '''
                Package cleanup could not be completed.
                You may need to restoart your OS to unlock relevant files and directories.

                The following packages are effected: "%s"
                ''',
                '", "'.join(sorted(self.failed_cleanup, key=lambda s: s.lower()))
            )
            return

        message = ''

        in_process = load_list_setting(self.pc_settings, 'in_process_packages')
        if in_process:
            message += 'to complete pending package operations on "%s"' \
                % '", "'.join(sorted(in_process, key=lambda s: s.lower()))

        if self.updated_libraries:
            if message:
                message += ' and '
            message += 'for installed or updated libraries to take effect.'
            message += ' Otherwise some packages may not work properly.'

        if message:
            show_message('Sublime Text needs to be restarted %s.' % message)

    def cleanup_pending_packages(self):
        """
        Scan through packages and complete pending operations

        The method ...
        1. replaces *.sublime-package files with *.sublime-package-new
        2. deletes package directories with a package-control.cleanup file
        3. clears package directories with a package-control.reinstall file
           and re-installs it.

        All found packages are considered `ignored_packages` and present/absent
        in `installed_packages` as related operation was interrupted or deferred
        before ST was restarted.

        :returns:
            A set of found packages.
        """

        found_packages = set()

        for file in os.listdir(sys_path.installed_packages_path()):
            package_name, file_extension = os.path.splitext(file)
            file_extension = file_extension.lower()

            # If there is a package file ending in .sublime-package-new, it
            # means that the .sublime-package file was locked when we tried
            # to upgrade, so the package was left in ignored_packages and
            # the user was prompted to restart Sublime Text. Now that the
            # package is not loaded, we can replace the old version with the
            # new one.
            if file_extension == '.sublime-package-new':
                new_file = os.path.join(sys_path.installed_packages_path(), file)
                package_file = get_installed_package_path(package_name)
                try:
                    try:
                        os.remove(package_file)
                    except FileNotFoundError:
                        pass

                    os.rename(new_file, package_file)
                    console_write(
                        '''
                        Finished replacing %s.sublime-package
                        ''',
                        package_name
                    )

                except OSError as e:
                    self.failed_cleanup.add(package_name)
                    console_write(
                        '''
                        Failed to replace %s.sublime-package with new package. %s
                        ''',
                        (package_name, e)
                    )

                found_packages.add(package_name)

            elif file_extension == '.sublime-package':
                found_packages.add(package_name)

        for package_name in os.listdir(sys_path.packages_path()):

            # Ignore `.`, `..` or hidden dot-directories
            if package_name[0] == '.':
                continue

            # Make sure not to clear user settings under all circumstances
            if package_name.lower() == 'user':
                continue

            # Ignore files
            package_dir = os.path.join(sys_path.packages_path(), package_name)
            if not os.path.isdir(package_dir):
                continue

            # Ignore hidden packages
            if os.path.exists(os.path.join(package_dir, '.hidden-sublime-package')):
                continue

            # Cleanup packages that could not be removed due to in-use files
            cleanup_file = os.path.join(package_dir, 'package-control.cleanup')
            if os.path.exists(cleanup_file):
                if delete_directory(package_dir):
                    console_write(
                        '''
                        Removed old package directory %s
                        ''',
                        package_name
                    )

                else:
                    self.failed_cleanup.add(package_name)
                    create_empty_file(cleanup_file)
                    console_write(
                        '''
                        Unable to remove old package directory "%s".
                        A restart of your computer may be required to unlock files.
                        ''',
                        package_name
                    )

                continue

            # Finish reinstalling packages that could not be upgraded due to in-use files
            reinstall_file = os.path.join(package_dir, 'package-control.reinstall')
            if os.path.exists(reinstall_file):
                if not clear_directory(package_dir):
                    self.failed_cleanup.add(package_name)
                    create_empty_file(reinstall_file)
                    console_write(
                        '''
                        Unable to clear package directory "%s" for re-install.
                        A restart of your computer may be required to unlock files.
                        ''',
                        package_name
                    )

                elif not self.manager.install_package(package_name):
                    create_empty_file(reinstall_file)

            found_packages.add(package_name)

        return found_packages

    def migrate_incompatible_packages(self, found_packages):
        """
        Determine and reinstall all incompatible packages

        :param found_packages:
            A set of found packages to verify compatibility for.

        :returns:
            A set of invalid packages which are not available for current ST or OS.
        """

        incompatible_packages = set(filter(lambda p: not self.manager.is_compatible(p), found_packages))
        if not incompatible_packages:
            return set()

        if self.pc_settings.get('auto_migrate', True):

            available_packages = set(self.manager.list_available_packages())
            migrate_packages = incompatible_packages & available_packages
            if migrate_packages:
                console_write(
                    'Migrating %s incompatible package%s...',
                    (len(migrate_packages), 's' if len(migrate_packages) != 1 else '')
                )

                reenable_packages = self.disable_packages({self.UPGRADE: migrate_packages})
                time.sleep(0.7)

                try:
                    for package_name in migrate_packages:
                        result = self.manager.install_package(package_name)

                        # re-enable if upgrade is not deferred to next start
                        if result is None and package_name in reenable_packages:
                            reenable_packages.remove(package_name)

                        # handle as compatible if update didn't explicitly fail
                        if result is not False:
                            incompatible_packages.remove(package_name)

                finally:
                    if reenable_packages:
                        time.sleep(0.7)
                        self.reenable_packages({self.UPGRADE: reenable_packages})

        if incompatible_packages:
            self.disable_packages({PackageDisabler.DISABLE: incompatible_packages})

            if len(incompatible_packages) == 1:
                message = '''
                    The following incompatible package was found installed:

                    - %s

                    It has been disabled as automatic migration was not possible!
                    '''
            else:
                message = '''
                    The following incompatible packages were found installed:

                    - %s

                    They have been disabled as automatic migration was not possible!
                    '''

            message += '''

                This is usually due to syncing packages across different
                machines in a way that does not check package metadata for
                compatibility.

                Please visit https://packagecontrol.io/docs/syncing for
                information about how to properly sync configuration and
                packages across machines.
                '''

            show_error(message, '\n- '.join(sorted(incompatible_packages, key=lambda s: s.lower())))

        return incompatible_packages

    def install_missing_libraries(self):
        missing_libraries = self.manager.find_missing_libraries()
        if not missing_libraries:
            return

        console_write(
            'Installing %s missing librar%s...',
            (len(missing_libraries), 'ies' if len(missing_libraries) != 1 else 'y')
        )

        for lib in missing_libraries:
            if self.manager.install_library(lib):
                self.updated_libraries = True

    def install_missing_packages(self, found_packages):
        """
        Install missing packages.

        Installs all packages that are listed in `installed_packages` setting
        of Package Control.sublime-settings but were not found on the filesystem
        and passed as `found_packages`.

        :param found_packages:
            A set of packages found on filesystem.
        """

        if not self.pc_settings.get('install_missing', True):
            return

        installed_packages = load_list_setting(self.pc_settings, 'installed_packages')
        missing_packages = installed_packages - found_packages
        if not missing_packages:
            return

        # Fetch a list of available (and renamed) packages and abort
        # if there are none available for installation.
        # An empty list indicates connection or configuration problems.
        available_packages = set(self.manager.list_available_packages())
        if not available_packages:
            return

        # Detect renamed packages and prepare batched install with new names.
        # Update `installed_packages` setting to remove old names without loosing something
        # in case installation fails.
        renamed_packages = self.manager.settings.get('renamed_packages', {})
        renamed_packages = {renamed_packages.get(p, p) for p in missing_packages}
        if renamed_packages != missing_packages:
            save_list_setting(
                self.pc_settings,
                self.pc_filename,
                'installed_packages',
                installed_packages - missing_packages | renamed_packages
            )

        # Make sure not to overwrite existing packages after renaming is applied.
        missing_packages = renamed_packages - found_packages
        if not missing_packages:
            return

        console_write(
            'Installing %s missing package%s...',
            (len(missing_packages), 's' if len(missing_packages) != 1 else '')
        )

        reenable_packages = self.disable_packages({self.INSTALL: missing_packages})
        time.sleep(0.7)

        try:
            for package_name in missing_packages:
                result = self.manager.install_package(package_name)

                # re-enable if upgrade is not deferred to next start
                if result is None and package_name in reenable_packages:
                    reenable_packages.remove(package_name)

        finally:
            if reenable_packages:
                time.sleep(0.7)
                self.reenable_packages({self.INSTALL: reenable_packages})

    def remove_orphaned_packages(self, found_packages):
        """
        Removes orphaned packages.

        The method removes all found and managed packages from filesystem,
        which are not present in `installed_packages`. They are considered
        active and therefore are disabled via PackageDisabler to properly
        reset theme/color scheme/syntax settings if needed.

        Compared to normal ``PackageManager.remove_package()` it doesn't
        - update `installed_packages` (not required)
        - remove orphaned libraries (will be done later)
        - send usage stats

        :param found_packages:
            A set of packages found on filesystem.

        :returns:
            A set of orphaned packages, which have successfully been removed.
        """

        if not self.pc_settings.get('remove_orphaned', True):
            return set()

        # find all managed orphaned packages
        orphaned_packages = set(filter(
            lambda p: package_file_exists(p, 'package-metadata.json'),
            found_packages - load_list_setting(self.pc_settings, 'installed_packages')
        ))

        if orphaned_packages:
            remover = PackageTaskRunner(self.manager)
            remover.remove_packages(orphaned_packages, package_kind='orphaned')

        return orphaned_packages
