import os

import sublime

from . import sys_path
from .package_manager import PackageManager
from .show_error import show_error
from .show_quick_panel import show_quick_panel


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

    def show_panel(self):
        """
        Shows a list of packages that can be turned into a .sublime-package file
        """

        self.packages = self.manager.list_packages(unpacked_only=True)
        if not self.packages:
            show_error(
                '''
                There are no packages available to be packaged
                '''
            )
            return
        show_quick_panel(self.window, self.packages, self.on_done)

    def on_done(self, picked):
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
            show_quick_panel(self.window, self.profiles, self.on_done_profile)
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

        if self.manager.create_package(self.package_name, destination, profile=self.profile):
            self.window.run_command(
                'open_dir',
                {
                    "dir": sys_path.shortpath(destination),
                    "file": self.package_name + '.sublime-package'
                }
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
