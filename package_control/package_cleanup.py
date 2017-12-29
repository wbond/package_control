import os
import threading
import time

import sublime

from . import __version__
from . import loader
from .automatic_upgrader import AutomaticUpgrader
from .clear_directory import clean_old_files
from .clear_directory import clear_directory
from .clear_directory import delete_directory
from .console_write import console_write
from .package_io import package_file_exists
from .path import installed_package_path
from .path import installed_packages_path
from .path import unpacked_package_path
from .path import unpacked_packages_path
from .package_manager import PackageManager
from .providers.release_selector import is_compatible_version
from .settings import load_list_setting
from .settings import pc_settings_filename
from .settings import preferences_filename
from .settings import save_list_setting
from .show_error import show_error


class PackageCleanup(threading.Thread):

    """
    Cleans up folders for packages that were removed, but that still have files
    in use.
    """

    def __init__(self):
        self.manager = PackageManager()

        settings = sublime.load_settings(pc_settings_filename())

        # We no longer use the installed_dependencies setting because it is not
        # necessary and created issues with settings shared across operating systems
        if settings.has('installed_dependencies'):
            settings.erase('installed_dependencies')
            sublime.save_settings(pc_settings_filename())

        self.original_installed_packages = load_list_setting(settings, 'installed_packages')
        self.remove_orphaned = settings.get('remove_orphaned', True)

        threading.Thread.__init__(self)

    def run(self):
        # This song and dance is necessary so Package Control doesn't try to clean
        # itself up, but also get properly marked as installed in the settings
        installed_packages_at_start = list(self.original_installed_packages)

        # Ensure we record the installation of Package Control itself
        if 'Package Control' not in installed_packages_at_start:
            params = {
                'package': 'Package Control',
                'operation': 'install',
                'version': __version__
            }
            self.manager.record_usage(params)
            installed_packages_at_start.append('Package Control')

        found_packages = []
        installed_packages = list(installed_packages_at_start)

        found_dependencies = []
        installed_dependencies = self.manager.list_dependencies()

        installed_path = installed_packages_path()

        for file in os.listdir(installed_path):

            package_name, package_ext = os.path.splitext(file)
            package_ext = package_ext.lower()

            if package_name == loader.loader_package_name:
                found_dependencies.append(package_name)
                continue

            # If there is a package file ending in .sublime-package-new, it
            # means that the .sublime-package file was locked when we tried
            # to upgrade, so the package was left in ignored_packages and
            # the user was prompted to restart Sublime Text. Now that the
            # package is not loaded, we can replace the old version with the
            # new one.
            if package_ext == '.sublime-package-new':
                package_file = installed_package_path(package_name)
                try:
                    try:
                        os.remove(package_file)
                    except FileNotFoundError:
                        pass
                    os.rename(os.path.join(installed_path, file), package_file)
                    console_write(
                        '''
                        Finished replacing %s.sublime-package
                        ''',
                        package_name
                    )
                except:
                    console_write(
                        '''
                        Error replacing %s.sublime-package
                        ''',
                        package_name
                    )
                continue

            if package_ext != '.sublime-package':
                continue

            # Cleanup packages that were installed via Package Control, but
            # we removed from the "installed_packages" list - usually by
            # removing them from another computer and the settings file
            # being synced.
            if self.remove_orphaned and package_name not in installed_packages_at_start \
                    and package_file_exists(package_name, 'package-metadata.json'):
                self.remove_package_file(package_name, os.path.join(installed_path, file))
                continue

            found_packages.append(package_name)

        required_dependencies = set(self.manager.find_required_dependencies())
        extra_dependencies = set(installed_dependencies) - required_dependencies

        # Clean up unneeded dependencies so that found_dependencies will only
        # end up having required dependencies added to it
        for dependency in extra_dependencies:
            dependency_dir = unpacked_package_path(dependency)
            if delete_directory(dependency_dir):
                console_write(
                    '''
                    Removed directory for unneeded dependency %s
                    ''',
                    dependency
                )
            else:
                cleanup_file = os.path.join(dependency_dir, 'package-control.cleanup')
                open(cleanup_file, 'wb').close()
                console_write(
                    '''
                    Unable to remove directory for unneeded dependency %s -
                    deferring until next start
                    ''',
                    dependency
                )
            # Make sure when cleaning up the dependency files that we remove the loader for it also
            loader.remove(dependency)

        for package_name in os.listdir(unpacked_packages_path()):
            found = True

            # ignore hidden directories
            if package_name[0] == '.':
                continue

            # ignore special packages
            if package_name in ('Default', 'User'):
                continue

            # ignore ordinary files
            package_dir = unpacked_package_path(package_name)
            if not os.path.isdir(package_dir):
                continue

            clean_old_files(package_dir)

            # Cleanup packages/dependencies that could not be removed due to in-use files
            cleanup_file = os.path.join(package_dir, 'package-control.cleanup')
            if os.path.exists(cleanup_file):
                if delete_directory(package_dir):
                    console_write(
                        '''
                        Removed old directory %s
                        ''',
                        package_name
                    )
                    found = False
                else:
                    open(cleanup_file, 'wb').close()
                    console_write(
                        '''
                        Unable to remove old directory %s - deferring until next start
                        ''',
                        package_name
                    )

            # Finish reinstalling packages that could not be upgraded due to in-use files
            reinstall = os.path.join(package_dir, 'package-control.reinstall')
            if os.path.exists(reinstall):
                metadata_path = os.path.join(package_dir, 'package-metadata.json')
                if not clear_directory(package_dir, [metadata_path]):
                    open(reinstall, 'wb').close()
                    show_error(
                        '''
                        An error occurred while trying to finish the upgrade of
                        %s. You will most likely need to restart your computer
                        to complete the upgrade.
                        ''',
                        package_name
                    )
                else:
                    self.manager.install_package(package_name)

            if package_file_exists(package_name, 'package-metadata.json'):
                # This adds previously installed packages from old versions of
                # PC. As of PC 3.0, this should basically never actually be used
                # since installed_packages was added in late 2011.
                if not installed_packages_at_start:
                    installed_packages.append(package_name)
                    params = {
                        'package': package_name,
                        'operation': 'install',
                        'version': self.manager.get_metadata(package_name).get('version')
                    }
                    self.manager.record_usage(params)

                # Cleanup packages that were installed via Package Control, but
                # we removed from the "installed_packages" list - usually by
                # removing them from another computer and the settings file
                # being synced.
                elif self.remove_orphaned and package_name not in installed_packages_at_start:
                    self.manager.backup_package_dir(package_name)
                    if delete_directory(package_dir):
                        console_write(
                            '''
                            Removed directory for orphaned package %s
                            ''',
                            package_name
                        )
                        found = False
                    else:
                        open(cleanup_file, 'wb').close()
                        console_write(
                            '''
                            Unable to remove directory for orphaned package %s -
                            deferring until next start
                            ''',
                            package_name
                        )

            if package_name.endswith('.package-control-old'):
                if delete_directory(package_dir):
                    console_write(
                        '''
                        Removed old directory %s
                        ''',
                        package_name
                    )

            # Skip over dependencies since we handle them separately
            if self.manager._is_dependency(package_name) and (
                    package_name == loader.loader_package_name or
                    loader.exists(package_name)):
                found_dependencies.append(package_name)
            elif found:
                found_packages.append(package_name)

        self.check_invalid_packages(found_packages, found_dependencies)
        self.finish(installed_packages, found_packages, found_dependencies)

    def remove_package_file(self, name, filename):
        """
        On Windows, .sublime-package files are locked when imported, so we must
        disable the package, delete it and then re-enable the package.

        :param name:
            The name of the package

        :param filename:
            The filename of the package
        """

        # Disable the package so any filesystem locks are released
        pref_filename = preferences_filename()
        settings = sublime.load_settings(pref_filename)
        ignored = load_list_setting(settings, 'ignored_packages')
        new_ignored = list(ignored)
        new_ignored.append(name)
        save_list_setting(settings, pref_filename, 'ignored_packages', new_ignored, ignored)

        # wait a little for ST to disable the package
        time.sleep(0.7)

        try:
            os.remove(filename)
            console_write(
                '''
                Removed orphaned package %s
                ''',
                name
            )

        except (OSError) as e:
            console_write(
                '''
                Unable to remove orphaned package %s - deferring until
                next start: %s
                ''',
                (name, str(e))
            )

        finally:
            # Always re-enable the package so it doesn't get stuck
            pref_filename = preferences_filename()
            settings = sublime.load_settings(pref_filename)
            ignored = load_list_setting(settings, 'ignored_packages')
            new_ignored = list(ignored)
            try:
                new_ignored.remove(name)
            except (ValueError):
                pass
            save_list_setting(settings, pref_filename, 'ignored_packages', new_ignored, ignored)

    def check_invalid_packages(self, found_packages, found_dependencies):

        # Check metadata to verify packages were not improperly installed
        invalid_packages = [
            package for package in found_packages
            if not self.is_compatible(self.manager.get_metadata(package))
        ]

        # Make sure installed dependencies are not improperly installed
        invalid_dependencies = [
            dependency for dependency in found_dependencies
            if not self.is_compatible(self.manager.get_metadata(dependency, is_dependency=True))
        ]

        if not invalid_packages and not invalid_dependencies:
            return

        message = ''
        if invalid_packages:
            package_s = 's were' if len(invalid_packages) != 1 else ' was'
            message += '''
                The following incompatible package%s found installed:

                %s

                ''' % (package_s, '\n'.join(invalid_packages))

        if invalid_dependencies:
            dependency_s = 'ies were' if len(invalid_dependencies) != 1 else 'y was'
            message += '''
                The following incompatible dependenc%s found installed:

                %s

                ''' % (dependency_s, '\n'.join(invalid_dependencies))

        message += '''
            This is usually due to syncing packages across different
            machines in a way that does not check package metadata for
            compatibility.

            Please visit https://packagecontrol.io/docs/syncing for
            information about how to properly sync configuration and
            packages across machines.

            To restore package functionality, please remove each listed
            package and reinstall it.
            '''
        show_error(message)

    def is_compatible(self, metadata):
        """
        Detects if a package is compatible with the current Sublime Text install

        :param metadata:
            A dict from a metadata file

        :return:
            If the package is compatible
        """

        sublime_text = metadata.get('sublime_text')
        platforms = metadata.get('platforms', [])

        # This indicates the metadata is old, so we assume a match
        if not sublime_text and not platforms:
            return True

        if not is_compatible_version(sublime_text):
            return False

        if not isinstance(platforms, list):
            platforms = [platforms]

        platform_selectors = [
            sublime.platform() + '-' + sublime.arch(),
            sublime.platform(),
            '*'
        ]

        for selector in platform_selectors:
            if selector in platforms:
                return True

        return False

    def finish(self, installed_packages, found_packages, found_dependencies):
        """
        A callback that can be run the main UI thread to perform saving of the
        Package Control.sublime-settings file. Also fires off the
        :class:`AutomaticUpgrader`.

        :param installed_packages:
            A list of the string package names of all "installed" packages,
            even ones that do not appear to be in the filesystem.

        :param found_packages:
            A list of the string package names of all packages that are
            currently installed on the filesystem.

        :param found_dependencies:
            A list of the string package names of all dependencies that are
            currently installed on the filesystem.
        """

        # Make sure we didn't accidentally ignore packages because something
        # was interrupted before it completed.
        pc_filename = pc_settings_filename()
        pc_settings = sublime.load_settings(pc_filename)

        in_process = load_list_setting(pc_settings, 'in_process_packages')
        if in_process:
            filename = preferences_filename()
            settings = sublime.load_settings(filename)

            ignored = load_list_setting(settings, 'ignored_packages')
            new_ignored = list(ignored)
            for package in in_process:
                if package in new_ignored:
                    # This prevents removing unused dependencies from being messed up by
                    # the functionality to re-enable packages that were left disabled
                    # by an error.
                    if loader.loader_package_name == package and loader.is_swapping():
                        continue
                    console_write(
                        '''
                        The package %s is being re-enabled after a Package
                        Control operation was interrupted
                        ''',
                        package
                    )
                    new_ignored.remove(package)

            save_list_setting(settings, filename, 'ignored_packages', new_ignored, ignored)
            save_list_setting(pc_settings, pc_filename, 'in_process_packages', [])

        save_list_setting(
            pc_settings,
            pc_filename,
            'installed_packages',
            installed_packages,
            self.original_installed_packages
        )
        AutomaticUpgrader(found_packages, found_dependencies).start()
