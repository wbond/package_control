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

    def run(self):
        pc_filename = pc_settings_filename()
        pc_settings = sublime.load_settings(pc_filename)

        # This song and dance is necessary so Package Control doesn't try to clean
        # itself up, but also get properly marked as installed in the settings
        # Ensure we record the installation of Package Control itself
        installed_packages = load_list_setting_as_set(pc_settings, 'installed_packages')
        if 'Package Control' not in installed_packages:
            self.manager.record_usage({
                'package': 'Package Control',
                'operation': 'install',
                'version': __version__
            })
            installed_packages.add('Package Control')
            save_list_setting(pc_settings, pc_filename, 'installed_packages', installed_packages)

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

        # Cleanup packages that were installed via Package Control, but we removed
        # from the "installed_packages" list - usually by removing them from another
        # computer and the settings file being synced.
        if pc_settings.get('remove_orphaned', True):
            removed_packages = self.remove_orphaned_packages(found_packages - installed_packages)
            found_packages -= removed_packages
        else:
            removed_packages = set()

        # Make sure we didn't accidentally ignore packages because something was
        # interrupted before it completed. Keep orphan packages disabled which
        # are deferred to next start.
        in_process = load_list_setting_as_set(pc_settings, 'in_process_packages') - removed_packages
        if in_process:
            console_write(
                "Re-enabling %d package%s after a Package Control operation was interrupted...",
                (len(in_process), 's' if len(in_process) != 1 else '')
            )
            PackageDisabler.reenable_packages(in_process, 'enable')

        # Check metadata to verify packages were not improperly installed
        self.migrate_incompatible_packages(found_packages)

        AutomaticUpgrader(found_packages).start()

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
