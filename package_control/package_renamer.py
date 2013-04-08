import os

import sublime

from .console_write import console_write
from .package_io import package_file_exists


class PackageRenamer():
    """
    Class to handle renaming packages via the renamed_packages setting
    gathered from channels and repositories.
    """

    def load_settings(self):
        """
        Loads the list of installed packages from the
        Package Control.sublime-settings file.
        """

        self.settings_file = 'Package Control.sublime-settings'
        self.settings = sublime.load_settings(self.settings_file)
        self.installed_packages = self.settings.get('installed_packages', [])
        if not isinstance(self.installed_packages, list):
            self.installed_packages = []

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
        installed_pkgs = self.installed_packages
        # There are the packages actually present on the filesystem
        present_packages = installer.manager.list_packages()

        # Rename directories for packages that have changed names
        for package_name in renamed_packages:
            package_dir = os.path.join(sublime.packages_path(), package_name)
            if not package_file_exists(package_name, 'package-metadata.json'):
                continue

            new_package_name = renamed_packages[package_name]
            new_package_dir = os.path.join(sublime.packages_path(),
                new_package_name)

            changing_case = package_name.lower() == new_package_name.lower()
            case_insensitive_fs = sublime.platform() in ['windows', 'osx']

            # Since Windows and OSX use case-insensitive filesystems, we have to
            # scan through the list of installed packages if the rename of the
            # package is just changing the case of it. If we don't find the old
            # name for it, we continue the loop since os.path.exists() will return
            # true due to the case-insensitive nature of the filesystems.
            if case_insensitive_fs and changing_case:
                has_old = False
                for present_package_name in present_packages:
                    if present_package_name == package_name:
                        has_old = True
                        break
                if not has_old:
                    continue

            if not os.path.exists(new_package_dir) or (case_insensitive_fs and changing_case):

                # Windows will not allow you to rename to the same name with
                # a different case, so we work around that with a temporary name
                if os.name == 'nt' and changing_case:
                    temp_package_name = '__' + new_package_name
                    temp_package_dir = os.path.join(sublime.packages_path(),
                        temp_package_name)
                    os.rename(package_dir, temp_package_dir)
                    package_dir = temp_package_dir

                os.rename(package_dir, new_package_dir)
                installed_pkgs.append(new_package_name)

                console_write(u'Renamed %s to %s' % (package_name, new_package_name), True)

            else:
                installer.manager.remove_package(package_name)
                message_string = u'Removed %s since package with new name (%s) already exists' % (
                    package_name, new_package_name)
                console_write(message_string, True)

            try:
                installed_pkgs.remove(package_name)
            except (ValueError):
                pass

        sublime.set_timeout(lambda: self.save_packages(installed_pkgs), 10)

    def save_packages(self, installed_packages):
        """
        Saves the list of installed packages (after having been appropriately
        renamed)

        :param installed_packages:
            The new list of installed packages
        """

        installed_packages = list(set(installed_packages))
        installed_packages = sorted(installed_packages,
            key=lambda s: s.lower())

        if installed_packages != self.installed_packages:
            self.settings.set('installed_packages', installed_packages)
            sublime.save_settings(self.settings_file)
