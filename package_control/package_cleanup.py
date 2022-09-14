import os
import threading
import time

import sublime

from . import sys_path, __version__
from .automatic_upgrader import AutomaticUpgrader
from .clear_directory import clear_directory, delete_directory
from .console_write import console_write
from .package_disabler import PackageDisabler
from .package_io import create_empty_file, get_installed_package_path, get_package_dir, package_file_exists
from .package_manager import PackageManager
from .settings import load_list_setting_as_set, pc_settings_filename, save_list_setting
from .show_error import show_error


class PackageCleanup(threading.Thread):

    """
    Cleans up folders for packages that were removed, but that still have files
    in use.
    """

    def __init__(self):
        threading.Thread.__init__(self)
        self.manager = PackageManager()
        self.pc_filename = pc_settings_filename()
        self.pc_settings = sublime.load_settings(self.pc_filename)

    def run(self):
        # This song and dance is necessary so Package Control doesn't try to clean
        # itself up, but also get properly marked as installed in the settings
        # Ensure we record the installation of Package Control itself
        installed_packages = load_list_setting_as_set(self.pc_settings, 'installed_packages')
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

        # Cleanup packages that were installed via Package Control, but we removed
        # from the "installed_packages" list - usually by removing them from another
        # computer and the settings file being synced.
        removed_packages = self.remove_orphaned_packages(found_packages - installed_packages)
        found_packages -= removed_packages

        # Make sure we didn't accidentally ignore packages because something was
        # interrupted before it completed. Keep orphan packages disabled which
        # are deferred to next start.
        in_process = load_list_setting_as_set(self.pc_settings, 'in_process_packages') - removed_packages
        if in_process:
            console_write(
                'Re-enabling %d package%s after a Package Control operation was interrupted...',
                (len(in_process), 's' if len(in_process) != 1 else '')
            )
            PackageDisabler.reenable_packages(in_process, 'enable')

        # Check metadata to verify packages were not improperly installed
        self.migrate_incompatible_packages(found_packages)

        self.install_missing_packages(found_packages)
        self.install_missing_libraries()

        self.manager.cleanup_libraries()

        AutomaticUpgrader().start()

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

        for file in os.listdir(sys_path.installed_packages_path):
            package_name, file_extension = os.path.splitext(file)
            file_extension = file_extension.lower()

            # If there is a package file ending in .sublime-package-new, it
            # means that the .sublime-package file was locked when we tried
            # to upgrade, so the package was left in ignored_packages and
            # the user was prompted to restart Sublime Text. Now that the
            # package is not loaded, we can replace the old version with the
            # new one.
            if file_extension == '.sublime-package-new':
                new_file = os.path.join(sys_path.installed_packages_path, file)
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
                    console_write(
                        '''
                        Failed to replace %s.sublime-package with new package. %s
                        ''',
                        (package_name, e)
                    )

                found_packages.add(package_name)

            elif file_extension == '.sublime-package':
                found_packages.add(package_name)

        for package_name in os.listdir(sys_path.packages_path):

            # Ignore `.`, `..` or hidden dot-directories
            if package_name[0] == '.':
                continue

            # Make sure not to clear user settings under all circumstances
            if package_name.lower() == 'user':
                continue

            # Ignore files
            package_dir = os.path.join(sys_path.packages_path, package_name)
            if not os.path.isdir(package_dir):
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
                    create_empty_file(cleanup_file)
                    console_write(
                        '''
                        Unable to remove old package directory %s -
                        deferring until next start
                        ''',
                        package_name
                    )

                continue

            # Finish reinstalling packages that could not be upgraded due to in-use files
            reinstall = os.path.join(package_dir, 'package-control.reinstall')
            if os.path.exists(reinstall):
                if clear_directory(package_dir) and self.manager.install_package(package_name):
                    console_write(
                        '''
                        Re-installed package %s
                        ''',
                        package_name
                    )

                else:
                    create_empty_file(reinstall)
                    console_write(
                        '''
                        Unable to re-install package %s -
                        deferring until next start
                        ''',
                        package_name
                    )

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

        available_packages = self.manager.list_available_packages()
        migrate_packages = set(filter(lambda p: p in available_packages, incompatible_packages))
        incompatible_packages = set()

        console_write(
            'Migrating %s incompatible package%s...',
            (len(migrate_packages), 's' if len(migrate_packages) != 1 else '')
        )

        reenable = PackageDisabler.disable_packages(migrate_packages, 'upgrade')
        time.sleep(0.7)

        try:
            for package_name in migrate_packages:
                result = self.manager.install_package(package_name)
                if result is None:
                    reenable.remove(package_name)
                    console_write(
                        '''
                        Unable to finalize migration of incompatible package %s -
                        deferring until next start
                        ''',
                        package_name
                    )
                elif result is False:
                    incompatible_packages.add(package_name)
                    console_write(
                        '''
                        Unable to migrate incompatible package %s
                        ''',
                        package_name
                    )
                else:
                    console_write(
                        '''
                        Migrated incompatible package %s
                        ''',
                        package_name
                    )

        finally:
            if reenable:
                time.sleep(0.7)
                PackageDisabler.reenable_packages(reenable, 'upgrade')

        if incompatible_packages:
            package_s = 's were' if len(incompatible_packages) != 1 else ' was'
            show_error(
                '''
                The following incompatible package%s found installed:

                %s

                This is usually due to syncing packages across different
                machines in a way that does not check package metadata for
                compatibility.

                Please visit https://packagecontrol.io/docs/syncing for
                information about how to properly sync configuration and
                packages across machines.
                ''',
                (package_s, '\n'.join(incompatible_packages))
            )

        return incompatible_packages

    def install_missing_libraries(self):
        missing_libraries = set(self.manager.find_required_libraries()) - set(self.manager.list_libraries())
        if not missing_libraries:
            return

        console_write(
            'Installing %s missing librar%s...',
            (len(missing_libraries), 'ies' if len(missing_libraries) != 1 else 'y')
        )

        libraries_installed = 0

        for lib in missing_libraries:
            if self.manager.install_library(lib.name, lib.python_version):
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

        installed_packages = load_list_setting_as_set(self.pc_settings, 'installed_packages')
        missing_packages = installed_packages - found_packages
        if not missing_packages:
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
                installed_packages - missing_packages + renamed_packages
            )

        # Make sure not to overwrite existing packages after renaming is applied.
        missing_packages = renamed_packages - found_packages
        if not missing_packages:
            return

        console_write(
            'Installing %s missing package%s...',
            (len(missing_packages), 's' if len(missing_packages) != 1 else '')
        )

        reenabled = PackageDisabler.disable_packages(missing_packages, 'install')
        time.sleep(0.7)

        try:
            for package_name in missing_packages:
                result = self.manager.install_package(package_name)
                if result is None:
                    reenabled.remove(package_name)
                    console_write(
                        '''
                        Unable to finalize install of missing package %s -
                        deferring until next start
                        ''',
                        package_name
                    )
                elif result is False:
                    console_write(
                        '''
                        Unable to install missing package %s
                        ''',
                        package_name
                    )
                else:
                    console_write(
                        '''
                        Installed missing package %s
                        ''',
                        package_name
                    )

        finally:
            if reenabled:
                time.sleep(0.7)
                PackageDisabler.reenable_packages(reenabled, 'install')

    def remove_orphaned_packages(self, orphaned_packages):
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

        :param orphaned_packages:
            A set of orphened package names

        :returns:
            A set of orphaned packages, which have successfully been removed.
        """

        if not self.pc_settings.get('remove_orphaned', True):
            return set()

        # find all managed orphaned packages
        orphaned_packages = set(filter(
            lambda p: package_file_exists(p, 'package-metadata.json'),
            orphaned_packages
        ))

        if not orphaned_packages:
            return set()

        console_write(
            'Removing %d orphaned package%s...',
            (len(orphaned_packages), 's' if len(orphaned_packages) != 1 else '')
        )

        # disable orphaned packages and reset theme, color scheme or syntaxes if needed
        reenable = PackageDisabler.disable_packages(orphaned_packages, 'remove')
        time.sleep(0.7)

        try:
            for package_name in orphaned_packages:
                cleanup_complete = True

                installed_package_path = get_installed_package_path(package_name)
                try:
                    os.remove(installed_package_path)
                    console_write(
                        '''
                        Removed orphaned package %s
                        ''',
                        package_name
                    )
                except FileNotFoundError:
                    pass
                except (OSError, IOError) as e:
                    console_write(
                        '''
                        Unable to remove orphaned package %s -
                        deferring until next start: %s
                        ''',
                        (package_name, e)
                    )
                    cleanup_complete = False

                package_dir = get_package_dir(package_name)
                can_delete_dir = os.path.exists(package_dir)
                if can_delete_dir:
                    self.manager.backup_package_dir(package_name)
                    if delete_directory(package_dir):
                        console_write(
                            '''
                            Removed directory for orphaned package %s
                            ''',
                            package_name
                        )

                    else:
                        create_empty_file(os.path.join(package_dir, 'package-control.cleanup'))
                        console_write(
                            '''
                            Unable to remove directory for orphaned package %s -
                            deferring until next start
                            ''',
                            package_name
                        )
                        cleanup_complete = False

                if not cleanup_complete:
                    reenable.remove(package_name)

        finally:
            if reenable:
                time.sleep(0.7)
                PackageDisabler.reenable_packages(reenable, 'remove')

        return orphaned_packages
