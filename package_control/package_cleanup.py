import os
import json
import threading
import time
import traceback

from . import sys_path, text, __version__
from .activity_indicator import ActivityIndicator
from .automatic_upgrader import AutomaticUpgrader
from .clear_directory import clear_directory, delete_directory
from .console_write import console_write
from .package_io import (
    create_empty_file,
    get_installed_package_path,
)
from .package_tasks import PackageTaskRunner
from .show_error import show_error, show_message


class PackageCleanup(threading.Thread, PackageTaskRunner):

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
        PackageTaskRunner.__init__(self)
        self.failed_cleanup = set()
        self.updated_libraries = False

    def run(self):
        # This song and dance is necessary so Package Control doesn't try to clean
        # itself up, but also get properly marked as installed in the settings
        # Ensure we record the installation of Package Control itself
        updated = self.manager.update_installed_packages(add='Package Control')
        if updated:
            self.manager.record_usage({
                'package': 'Package Control',
                'operation': 'install',
                'version': __version__
            })
            if self.manager.settings.get('debug'):
                console_write("Prevented Package Control from removing itself.")

        # To limit disk space occupied remove all old enough backups
        self.manager.prune_backup_dir()

        # Clear trash
        clear_directory(sys_path.trash_path())

        # Cleanup disabled python environments
        self.cleanup_python_environments()

        # Scan through packages and complete pending operations
        found_packages = self.cleanup_pending_packages()

        # Clean-up packages that were installed via Package Control, but have been
        # removed from the "installed_packages" list - usually by removing them
        # from another computer and the settings file being synced.
        removed_packages = self.remove_orphaned_packages(found_packages)
        found_packages -= removed_packages

        # Make sure we didn't accidentally ignore packages because something was
        # interrupted before it completed. Keep orphaned packages disabled which
        # are deferred to next start.
        in_process = self.in_process_packages() - removed_packages
        if in_process:
            console_write(
                'Re-enabling %d package%s after a Package Control operation was interrupted...',
                (len(in_process), 's' if len(in_process) != 1 else '')
            )

        # Remove non-existing packages from ignored_packages list.
        orphaned_ignored_packages = self.ignored_packages() - found_packages \
            - self.manager.list_default_packages()

        if in_process or orphaned_ignored_packages:
            self.reenable_packages({self.ENABLE: in_process | orphaned_ignored_packages})

        # garbage collect no longer needed sets
        in_process = None
        orphaned_ignored_packages = None
        removed_packages = None

        # Check metadata to verify packages were not improperly installed
        self.migrate_incompatible_packages(found_packages)

        self.install_missing_packages(found_packages)

        if self.manager.settings.get('remove_orphaned', True):
            self.manager.cleanup_libraries()

        self.install_missing_libraries()

        if self.manager.settings.get('auto_upgrade'):
            AutomaticUpgrader(self.manager).run()

        # make sure to restore indexing state
        # note: required after Package Control upgrade
        self.resume_indexer()

        if self.failed_cleanup:
            show_error(
                '''
                Package clean-up could not be completed.
                You may need to restart your OS to unlock relevant files and directories.

                The following packages are affected: "%s"
                ''',
                '", "'.join(sorted(self.failed_cleanup, key=lambda s: s.lower()))
            )
            return

        message = ''

        in_process = self.in_process_packages()
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

    def cleanup_python_environments(self):
        """
        Remove library and cache folders of disabled or absent plugin_hosts.
        """
        if not self.manager.settings.get('remove_orphaned_enviornments'):
            return

        # actual library dir
        libdir = os.path.join(sys_path.data_path(), "Lib", "python")
        # portable cache dir
        cache1 = os.path.join(sys_path.cache_path(), "__pycache__", "install", "Data", "Lib", "python")
        # normal setup's cache dir
        cache2 = os.path.join(sys_path.cache_path(), "__pycache__", "data", "Lib", "python")

        supported_versions = sys_path.python_versions()
        if "3.3" not in supported_versions:
            # Python folder is re-created at each startup, hence just clear it for now.
            clear_directory(libdir + "33")
            # Python 3.3 itself doesn't support nor create compiled cache modules,
            # ST's fallback mechanism might however have created some py38 or py313 cache files
            # in those directories, which need to be cleared out.
            delete_directory(cache1 + "33")
            delete_directory(cache2 + "33")

        if "3.8" not in supported_versions:
            # if 3.8 is not supported it is not present, delete all folders
            delete_directory(libdir + "38")
            delete_directory(cache1 + "38")
            delete_directory(cache2 + "38")

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

            # Clean-up packages that could not be removed due to in-use files
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

                elif not self.manager.install_package(package_name, unattended=True):
                    create_empty_file(reinstall_file)

            # Convert unpacked managed package into unmanaged package,
            # if folder name no longer matches original package name,
            # in order to avoid it being removed as orphaned.
            try:
                clear = False
                metadata_file = os.path.join(package_dir, 'package-metadata.json')

                with open(metadata_file, 'r', encoding='utf-8') as fobj:
                    metadata = json.load(fobj)
                    clear = metadata['name'] != package_name

                if clear:
                    os.remove(metadata_file)
                    console_write(
                        '''
                        Package "%s" is now unmanaged as it was renamed by user.
                        ''',
                        package_name
                    )

            except (OSError, KeyError, ValueError):
                pass

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

        incompatible_packages = set(filter(
            lambda p: not self.manager.is_compatible(p),
            found_packages - self.ignored_packages()
        ))
        if not incompatible_packages:
            return set()

        if self.manager.settings.get('auto_migrate', True):
            available_packages = set(self.manager.list_available_packages())
            migrate_packages = incompatible_packages & available_packages
            if migrate_packages:
                num_packages = len(migrate_packages)
                if num_packages == 1:
                    message = 'Migrating package {}'.format(list(migrate_packages)[0])
                else:
                    message = 'Migrating {} packages...'.format(num_packages)
                    console_write(message)

                with ActivityIndicator(message) as progress:
                    reenable_packages = self.disable_packages({self.UPGRADE: migrate_packages})
                    time.sleep(0.7)

                    num_success = 0

                    for package_name in sorted(migrate_packages, key=lambda s: s.lower()):
                        try:
                            progress.set_label('Migrating package {}...'.format(package_name))
                            result = self.manager.install_package(package_name, unattended=True)
                            if result is True:
                                num_success += 1

                            # re-enable if upgrade is not deferred to next start
                            if result is None and package_name in reenable_packages:
                                reenable_packages.remove(package_name)

                            # handle as compatible if update didn't explicitly fail
                            if result is not False:
                                incompatible_packages.remove(package_name)

                        except Exception as e:
                            traceback.print_tb(e.__traceback__)

                    if num_packages == 1:
                        message = 'Package {} successfully migrated'.format(list(migrate_packages)[0])
                    elif num_packages == num_success:
                        message = 'All packages successfully migrated'
                        console_write(message)
                    else:
                        message = '{} of {} packages successfully migrated'.format(num_success, num_packages)
                        console_write(message)

                    if reenable_packages:
                        time.sleep(0.7)
                        self.reenable_packages({self.UPGRADE: reenable_packages})

                    progress.finish(message)

        if incompatible_packages:
            self.remove_packages(incompatible_packages, package_kind='incompatible')

            if len(incompatible_packages) == 1:
                message = text.format(
                    '''
                    The following incompatible package was found installed:

                    - %s

                    It has been removed as migration was not possible!
                    ''',
                    incompatible_packages
                )
            else:
                message = text.format(
                    '''
                    The following incompatible packages were found installed:

                    - %s

                    They have been removed as migration was not possible!
                    ''',
                    ('\n- '.join(sorted(incompatible_packages, key=lambda s: s.lower())))
                )

            message += text.format(
                '''

                This is usually due to syncing packages across different
                machines in a way that does not check package metadata for
                compatibility.

                Please visit https://packagecontrol.io/docs/syncing for
                information about how to properly sync configuration and
                packages across machines.
                '''
            )

            show_message(message)

        return incompatible_packages

    def install_missing_libraries(self):
        missing_libraries = self.manager.find_missing_libraries()
        if not missing_libraries:
            return

        num_libraries = len(missing_libraries)
        if num_libraries == 1:
            message = 'Installing library {}'.format(list(missing_libraries)[0])
        else:
            message = 'Installing {} libraries...'.format(num_libraries)
            console_write(message)

        with ActivityIndicator(message) as progress:
            for lib in missing_libraries:
                progress.set_label('Installing library {}'.format(lib.name))
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

        if not self.manager.settings.get('install_missing', True):
            return

        installed_packages = self.manager.installed_packages()

        tasks = self.create_package_tasks(
            actions=(self.INSTALL, self.OVERWRITE),
            include_packages=installed_packages,
            found_packages=found_packages
        )
        if tasks:
            with ActivityIndicator('Installing missing packages...') as progress:
                self.run_install_tasks(tasks, progress, unattended=True, package_kind='missing')

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

        if not self.manager.settings.get('remove_orphaned', True):
            return set()

        # find all managed orphaned packages
        orphaned_packages = set(filter(
            self.manager.is_managed,
            found_packages - self.manager.installed_packages()
        ))

        if orphaned_packages:
            with ActivityIndicator('Removing orphaned packages...') as progress:
                self.remove_packages(orphaned_packages, package_kind='orphaned', progress=progress)

        return orphaned_packages
