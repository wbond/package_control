import compileall
import os
import zipfile

import sublime

from fnmatch import fnmatch

from . import sys_path
from .package_manager import PackageManager
from .package_io import get_package_dir
from .show_error import show_error, show_message


class PackageCreator:

    """
    Abstract class for commands that create .sublime-package files
    """

    def __init__(self, window):
        """
        Constructs a new instance.

        :param window:
            The ``sublime.Window`` object the task is invoked from.
        """

        self.window = window
        self.manager = PackageManager()

    def run(self):
        """
        Shows a list of packages that can be turned into a .sublime-package file
        """

        self.packages = self.manager.list_packages(unpacked_only=True)
        if not self.packages:
            show_message('There are no packages available to be packaged')
            return

        self.window.show_quick_panel(
            self.packages,
            self.on_done_packages,
            sublime.KEEP_OPEN_ON_FOCUS_LOST
        )

    def on_done_packages(self, picked):
        """
        Quick panel user selection handler - processes the user package
        selection and prompts the user to pick a profile, or just creates the
        package file if there are no profiles

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        self.profile = None

        if picked == -1:
            return
        self.package_name = self.packages[picked]

        rules = self.manager.settings.get('package_profiles')
        if not rules:
            self.select_destination()
            return

        self.profiles = ['Default']
        for key in rules.keys():
            self.profiles.append(key)

        def show_panel():
            self.window.show_quick_panel(
                self.profiles,
                self.on_done_profile,
                sublime.KEEP_OPEN_ON_FOCUS_LOST
            )
        sublime.set_timeout(show_panel, 50)

    def on_done_profile(self, picked):
        """
        Quick panel user selection handler - processes the package profile
        selection and creates the package file

        :param picked:
            An integer of the 0-based profile name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return

        # If the user picks a profile
        if picked > 0:
            self.profile = self.profiles[picked]

        self.select_destination()

    def select_destination(self):
        """
        Display Select Folder Dialog to retrieve the destination for .sublime-package files
        """

        destination = self.get_package_destination()

        if hasattr(sublime, 'select_folder_dialog'):
            sublime.select_folder_dialog(self.do_create_package, directory=destination)
        else:
            self.do_create_package(destination)

    def do_create_package(self, destination):
        """
        Calls into the PackageManager to actually create the package file
        """

        if destination is None:
            return

        package_dir = get_package_dir(self.package_name)
        if not os.path.isdir(package_dir):
            show_error(
                '''
                The folder for the package name specified, %s,
                does not exists in %s
                ''',
                (self.package_name, sys_path.packages_path())
            )
            return False

        package_filename = self.package_name + '.sublime-package'
        package_path = os.path.join(destination, package_filename)

        try:
            os.makedirs(destination, exist_ok=True)

            with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as package_file:

                compileall.compile_dir(package_dir, quiet=True, legacy=True, optimize=2)

                profile_settings = self.manager.settings.get('package_profiles', {}).get(self.profile)

                def get_profile_setting(setting, default):
                    if profile_settings:
                        profile_value = profile_settings.get(setting)
                        if profile_value is not None:
                            return profile_value
                    return self.manager.settings.get(setting, default)

                dirs_to_ignore = get_profile_setting('dirs_to_ignore', [])
                files_to_ignore = get_profile_setting('files_to_ignore', [])
                files_to_include = get_profile_setting('files_to_include', [])

                for root, dirs, files in os.walk(package_dir):
                    # remove all "dirs_to_ignore" from "dirs" to make os.walk ignore them
                    dirs[:] = [x for x in dirs if x not in dirs_to_ignore]
                    for file in files:
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, package_dir)

                        ignore_matches = (fnmatch(relative_path, p) for p in files_to_ignore)
                        include_matches = (fnmatch(relative_path, p) for p in files_to_include)
                        if any(ignore_matches) and not any(include_matches):
                            continue

                        package_file.write(full_path, relative_path)

            self.window.run_command(
                'open_dir',
                {
                    "dir": sys_path.shortpath(destination),
                    "file": self.package_name + '.sublime-package'
                }
            )

        except (IOError, OSError) as e:
            show_error(
                '''
                An error occurred creating the package file %s in %s.

                %s
                ''',
                (package_filename, destination, e)
            )

    def get_package_destination(self):
        """
        Retrieves the destination for .sublime-package files

        :return:
            A string - the path to the folder to save .sublime-package files in
        """

        destination = None

        if self.profile:
            profile_settings = self.manager.settings.get('package_profiles', {}).get(self.profile, {})
            destination = profile_settings.get('package_destination')

        if not destination:
            destination = self.manager.settings.get('package_destination')

            # We check destination via an if statement instead of using
            # the dict.get() method since the key may be set, but to a blank value
            if not destination:
                destination = os.environ.get('XDG_DESKTOP_DIR', '')

                if not destination:
                    destination = os.path.join(os.path.expanduser('~'), 'Desktop')

        return os.path.normpath(os.path.expandvars(destination))
