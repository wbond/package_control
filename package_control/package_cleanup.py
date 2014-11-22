import threading
import os

import sublime

from .show_error import show_error
from .console_write import console_write
from .unicode import unicode_from_os
from .rmtree import rmtree
from .clear_directory import clear_directory
from .automatic_upgrader import AutomaticUpgrader
from .package_manager import PackageManager
from .open_compat import open_compat
from .package_io import package_file_exists
from .settings import preferences_filename, pc_settings_filename, load_list_setting, save_list_setting


class PackageCleanup(threading.Thread):
    """
    Cleans up folders for packages that were removed, but that still have files
    in use.
    """

    def __init__(self):
        self.manager = PackageManager()

        settings = sublime.load_settings(pc_settings_filename())
        self.original_installed_packages = load_list_setting(settings, 'installed_packages')
        self.remove_orphaned = settings.get('remove_orphaned', True)

        threading.Thread.__init__(self)

    def run(self):
        found_packages = []
        installed_packages = list(self.original_installed_packages)

        for package_name in os.listdir(sublime.packages_path()):
            found = True

            package_dir = os.path.join(sublime.packages_path(), package_name)

            # Cleanup packages that could not be removed due to in-use files
            cleanup_file = os.path.join(package_dir, 'package-control.cleanup')
            if os.path.exists(cleanup_file):
                try:
                    rmtree(package_dir)
                    console_write(u'Removed old directory for package %s' % package_name, True)
                    found = False

                except (OSError) as e:
                    if not os.path.exists(cleanup_file):
                        open_compat(cleanup_file, 'w').close()

                    error_string = (u'Unable to remove old directory for package ' +
                        u'%s - deferring until next start: %s') % (
                        package_name, unicode_from_os(e))
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
                    try:
                        self.manager.backup_package_dir(package_name)
                        rmtree(package_dir)
                        console_write(u'Removed directory for orphaned package %s' % package_name, True)
                        found = False

                    except (OSError) as e:
                        if not os.path.exists(cleanup_file):
                            open_compat(cleanup_file, 'w').close()

                        error_string = (u'Unable to remove directory for orphaned package ' +
                            u'%s - deferring until next start: %s') % (
                            package_name, unicode_from_os(e))
                        console_write(error_string, True)

            if found:
                found_packages.append(package_name)

        if int(sublime.version()) >= 3000:
            installed_path = sublime.installed_packages_path()

            for file in os.listdir(installed_path):
                package_name = file.replace('.sublime-package', '')

                # Cleanup packages that were installed via Package Control, but
                # we removed from the "installed_packages" list - usually by
                # removing them from another computer and the settings file
                # being synced.
                if self.remove_orphaned and package_name not in self.original_installed_packages and package_file_exists(package_name, 'package-metadata.json'):
                    try:
                        os.remove(os.path.join(installed_path, file))
                        console_write(u'Removed orphaned package %s' % package_name, True)

                    except (OSError):
                        error_string = (u'Unable to remove orphaned package ' +
                            u'%s - deferring until next start: %s') % (
                            package_name, unicode_from_os(e))
                        console_write(error_string, True)

                else:
                    found_packages.append(package_name)

        sublime.set_timeout(lambda: self.finish(installed_packages, found_packages), 10)

    def finish(self, installed_packages, found_packages):
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

        save_list_setting(pc_settings, pc_filename, 'installed_packages',
            installed_packages, self.original_installed_packages)
        AutomaticUpgrader(found_packages).start()
