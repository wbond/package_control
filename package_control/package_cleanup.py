import threading
import os

import sublime

from .show_error import show_error
from .console_write import console_write
from .unicode import unicode_from_os
from .clear_directory import clear_directory, delete_directory, clean_old_files
from .automatic_upgrader import AutomaticUpgrader
from .package_manager import PackageManager
from .open_compat import open_compat
from .package_io import package_file_exists
from .settings import preferences_filename, pc_settings_filename, load_list_setting, save_list_setting
from . import loader
from .providers.release_selector import is_compatible_version


class PackageCleanup(threading.Thread):
    """
    Cleans up folders for packages that were removed, but that still have files
    in use.
    """

    def __init__(self):
        self.manager = PackageManager()

        settings = sublime.load_settings(pc_settings_filename())
        self.original_installed_packages = load_list_setting(settings, 'installed_packages')
        self.original_installed_dependencies = load_list_setting(settings, 'installed_dependencies')
        self.remove_orphaned = settings.get('remove_orphaned', True)

        threading.Thread.__init__(self)

    def run(self):
        found_packages = []
        found_dependencies = []

        installed_packages = list(self.original_installed_packages)
        installed_dependencies = list(self.original_installed_dependencies)

        for package_name in os.listdir(sublime.packages_path()):
            found = True

            package_dir = os.path.join(sublime.packages_path(), package_name)
            if not os.path.isdir(package_dir):
                continue

            clean_old_files(package_dir)

            # Cleanup packages that could not be removed due to in-use files
            cleanup_file = os.path.join(package_dir, 'package-control.cleanup')
            if os.path.exists(cleanup_file):
                if delete_directory(package_dir):
                    console_write(u'Removed old directory for package %s' % package_name, True)
                    found = False
                else:
                    if not os.path.exists(cleanup_file):
                        open_compat(cleanup_file, 'w').close()
                    error_string = (u'Unable to remove old directory for package ' +
                        u'%s - deferring until next start') % package_name
                    console_write(error_string, True)

            # Finish reinstalling packages that could not be upgraded due to
            # in-use files
            reinstall = os.path.join(package_dir, 'package-control.reinstall')
            if os.path.exists(reinstall):
                metadata_path = os.path.join(package_dir, 'package-metadata.json')
                if not clear_directory(package_dir, [metadata_path]):
                    if not os.path.exists(reinstall):
                        open_compat(reinstall, 'w').close()
                    # Assigning this here prevents the callback from referencing the value
                    # of the "package_name" variable when it is executed
                    restart_message = (u'An error occurred while trying to ' +
                        u'finish the upgrade of %s. You will most likely need to ' +
                        u'restart your computer to complete the upgrade.') % package_name

                    def show_still_locked():
                        show_error(restart_message)
                    sublime.set_timeout(show_still_locked, 10)
                else:
                    self.manager.install_package(package_name)

            if package_file_exists(package_name, 'package-metadata.json'):
                # This adds previously installed packages from old versions of
                # PC. As of PC 3.0, this should basically never actually be used
                # since installed_packages was added in late 2011.
                if not self.original_installed_packages:
                    installed_packages.append(package_name)
                    params = {
                        'package': package_name,
                        'operation': 'install',
                        'version': \
                            self.manager.get_metadata(package_name).get('version')
                    }
                    self.manager.record_usage(params)

                # Cleanup packages that were installed via Package Control, but
                # we removed from the "installed_packages" list - usually by
                # removing them from another computer and the settings file
                # being synced.
                elif self.remove_orphaned and package_name not in self.original_installed_packages:
                    self.manager.backup_package_dir(package_name)
                    if delete_directory(package_dir):
                        console_write(u'Removed directory for orphaned package %s' % package_name, True)
                        found = False
                    else:
                        if not os.path.exists(cleanup_file):
                            open_compat(cleanup_file, 'w').close()
                        error_string = (u'Unable to remove directory for orphaned package ' +
                            u'%s - deferring until next start') % package_name
                        console_write(error_string, True)

            if package_file_exists(package_name, 'dependency-metadata.json'):
                found = False
                if self.remove_orphaned and package_name not in self.original_installed_dependencies:
                    if delete_directory(package_dir):
                        console_write(u'Removed directory for orphaned dependency %s' % package_name, True)
                    else:
                        if not os.path.exists(cleanup_file):
                            open_compat(cleanup_file, 'w').close()
                        error_string = (u'Unable to remove directory for orphaned dependency ' +
                            u'%s - deferring until next start') % package_name
                        console_write(error_string, True)
                else:
                    found_dependencies.append(package_name)

            if found:
                found_packages.append(package_name)

        if int(sublime.version()) >= 3000:
            installed_path = sublime.installed_packages_path()

            for file in os.listdir(installed_path):
                if file[-16:] != '.sublime-package':
                    continue

                package_name = file.replace('.sublime-package', '')

                if package_name == loader.loader_package_name:
                    found_dependencies.append(package_name)
                    continue

                # Cleanup packages that were installed via Package Control, but
                # we removed from the "installed_packages" list - usually by
                # removing them from another computer and the settings file
                # being synced.
                if self.remove_orphaned and package_name not in self.original_installed_packages and package_file_exists(package_name, 'package-metadata.json'):
                    # Since Windows locks the .sublime-package files, we must
                    # do a dance where we disable the package first, which has
                    # to be done in the main Sublime Text thread.
                    package_filename = os.path.join(installed_path, file)
                    # Invoke a function to build the callback since we are in a loop
                    # and the variable values will change by the time the callback is
                    # actually called
                    def build_lambda(name, filename):
                        return lambda: self.remove_package_file(name, filename)
                    sublime.set_timeout(build_lambda(package_name, package_filename), 10)

                else:
                    found_packages.append(package_name)

        invalid_packages = []
        invalid_dependencies = []

        # Check metadata to verify packages were not improperly installed, and
        # also make sure we have all dependencies we need
        for package in found_packages:
            if package == 'User':
                continue

            metadata = self.manager.get_metadata(package)
            if metadata:
                if not self.is_compatible(metadata):
                    invalid_packages.append(package)

            for dependency in self.manager.get_dependencies(package):
                if dependency not in installed_dependencies:
                    installed_dependencies.append(dependency)

        for dependency in found_dependencies:
            metadata = self.manager.get_metadata(dependency, is_dependency=True)
            if metadata and not self.is_compatible(metadata):
                invalid_dependencies.append(package)

        if invalid_packages or invalid_dependencies:
            def show_sync_error():
                message = u''
                if invalid_packages:
                    package_s = 's were' if len(invalid_packages) != 1 else ' was'
                    message += (u'The following incompatible package%s ' + \
                        u'found installed:\n\n%s\n\n') % (package_s,
                        '\n'.join(invalid_packages))
                if invalid_dependencies:
                    dependency_s = 'ies were' if len(invalid_dependencies) != 1 else 'y was'
                    message += (u'The following incompatible dependenc%s ' + \
                        u'found installed:\n\n%s\n\n') % (dependency_s,
                        '\n'.join(invalid_dependencies))
                message += u'This is usually due to syncing packages across ' + \
                    u'different machines in a way that does not check ' + \
                    u'package metadata for compatibility.\n\n' + \
                    u'Please visit https://packagecontrol.io/docs/syncing ' + \
                    u'for information about how to properly sync ' + \
                    u'configuration and packages across machines.\n\n' + \
                    u'To restore package functionality, please remove each ' + \
                    u'listed package and reinstall it.'
                show_error(message)
            sublime.set_timeout(show_sync_error, 100)

        sublime.set_timeout(lambda: self.finish(installed_packages, installed_dependencies, found_packages, found_dependencies), 10)

    def remove_package_file(self, name, filename):
        """
        On Windows, .sublime-package files are locked when imported, so we must
        disable the package, delete it and then re-enable the package.

        :param name:
            The name of the package

        :param filename:
            The filename of the package
        """

        def do_remove():
            try:
                os.remove(filename)
                console_write(u'Removed orphaned package %s' % name, True)

            except (OSError) as e:
                error_string = (u'Unable to remove orphaned package ' +
                    u'%s - deferring until next start: %s') % (
                    name, unicode_from_os(e))
                console_write(error_string, True)

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

        # Disable the package so any filesystem locks are released
        pref_filename = preferences_filename()
        settings = sublime.load_settings(pref_filename)
        ignored = load_list_setting(settings, 'ignored_packages')
        new_ignored = list(ignored)
        new_ignored.append(name)
        save_list_setting(settings, pref_filename, 'ignored_packages', new_ignored, ignored)

        sublime.set_timeout(do_remove, 700)

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

        platform_selectors = [sublime.platform() + '-' + sublime.arch(),
            sublime.platform(), '*']

        for selector in platform_selectors:
            if selector in platforms:
                return True

        return False

    def finish(self, installed_packages, installed_dependencies, found_packages, found_dependencies):
        """
        A callback that can be run the main UI thread to perform saving of the
        Package Control.sublime-settings file. Also fires off the
        :class:`AutomaticUpgrader`.

        :param installed_packages:
            A list of the string package names of all "installed" packages,
            even ones that do not appear to be in the filesystem.

        :param installed_dependencies:
            A list of the string dependency names of all "installed"
            dependencies, even ones that do not appear to be in the filesystem.

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
                    console_write(u'The package %s is being re-enabled after a Package Control operation was interrupted' % package, True)
                    new_ignored.remove(package)

            save_list_setting(settings, filename, 'ignored_packages', new_ignored, ignored)
            save_list_setting(pc_settings, pc_filename, 'in_process_packages', [])

        save_list_setting(pc_settings, pc_filename, 'installed_dependencies',
            installed_dependencies, self.original_installed_dependencies)

        save_list_setting(pc_settings, pc_filename, 'installed_packages',
            installed_packages, self.original_installed_packages)
        AutomaticUpgrader(found_packages, found_dependencies).start()
