import os
import time

import sublime

from .console_write import console_write
from .package_disabler import PackageDisabler
from .settings import pc_settings_filename, load_list_setting, save_list_setting


class PackageRenamer(PackageDisabler):
    """
    Class to handle renaming packages via the renamed_packages setting
    gathered from channels and repositories.
    """

    def load_settings(self):
        """
        Loads the list of installed packages
        """

        settings = sublime.load_settings(pc_settings_filename())
        self.original_installed_packages = load_list_setting(settings, 'installed_packages')

    def rename_packages(self, installer):
        """
        Renames any installed packages that the user has installed.

        :param installer:
            An instance of :class:`PackageInstaller`
        """

        # Fetch the packages since that will pull in the renamed packages list
        installer.manager.list_available_packages()
        renamed_packages = installer.manager.settings.get('renamed_packages', {})

        if not renamed_packages:
            renamed_packages = {}

        # These are packages that have been tracked as installed
        installed_packages = list(self.original_installed_packages)
        # There are the packages actually present on the filesystem
        present_packages = installer.manager.list_packages()

        case_insensitive_fs = sublime.platform() in ['windows', 'osx']

        # Rename directories for packages that have changed names
        for package_name in renamed_packages:
            new_package_name = renamed_packages[package_name]
            changing_case = package_name.lower() == new_package_name.lower()

            # Since Windows and OSX use case-insensitive filesystems, we have to
            # scan through the list of installed packages if the rename of the
            # package is just changing the case of it. If we don't find the old
            # name for it, we continue the loop since os.path.exists() will return
            # true due to the case-insensitive nature of the filesystems.
            has_old = False
            if case_insensitive_fs and changing_case:
                for present_package_name in present_packages:
                    if present_package_name == package_name:
                        has_old = True
                        break
                if not has_old:
                    continue

            # For handling .sublime-package files
            package_file = os.path.join(sublime.installed_packages_path(),
                package_name + '.sublime-package')
            # For handling unpacked packages
            package_dir = os.path.join(sublime.packages_path(), package_name)

            if os.path.exists(package_file):
                new_package_path = os.path.join(sublime.installed_packages_path(),
                    new_package_name + '.sublime-package')
                package_path = package_file
            elif os.path.exists(os.path.join(package_dir, 'package-metadata.json')):
                new_package_path = os.path.join(sublime.packages_path(),
                    new_package_name)
                package_path = package_dir
            else:
                continue

            sublime.set_timeout(lambda: self.disable_packages(package_name, 'remove'), 10)

            if not os.path.exists(new_package_path) or (case_insensitive_fs and changing_case):
                sublime.set_timeout(lambda: self.disable_packages(new_package_name, 'install'), 10)
                time.sleep(0.7)

                # Windows will not allow you to rename to the same name with
                # a different case, so we work around that with a temporary name
                if os.name == 'nt' and changing_case:
                    temp_package_name = '__' + new_package_name
                    temp_package_path = os.path.join(sublime.packages_path(),
                        temp_package_name)
                    os.rename(package_path, temp_package_path)
                    package_path = temp_package_path

                os.rename(package_path, new_package_path)
                installed_packages.append(new_package_name)

                console_write(u'Renamed %s to %s' % (package_name, new_package_name), True)
                sublime.set_timeout(lambda: self.reenable_package(new_package_name, 'install'), 700)

            else:
                time.sleep(0.7)
                installer.manager.remove_package(package_name)
                message_string = u'Removed %s since package with new name (%s) already exists' % (
                    package_name, new_package_name)
                console_write(message_string, True)

            sublime.set_timeout(lambda: self.reenable_package(package_name, 'remove'), 700)

            try:
                installed_packages.remove(package_name)
            except (ValueError):
                pass

        sublime.set_timeout(lambda: self.save_packages(installed_packages), 10)

    def save_packages(self, installed_packages):
        """
        Saves the list of installed packages (after having been appropriately
        renamed)

        :param installed_packages:
            The new list of installed packages
        """

        filename = pc_settings_filename()
        settings = sublime.load_settings(filename)
        save_list_setting(settings, filename, 'installed_packages',
            installed_packages, self.original_installed_packages)
