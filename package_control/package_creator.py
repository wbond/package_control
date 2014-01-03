import os

import sublime

from .show_error import show_error
from .package_manager import PackageManager


class PackageCreator():
    """
    Abstract class for commands that create .sublime-package files
    """

    def show_panel(self):
        """
        Shows a list of packages that can be turned into a .sublime-package file
        """

        self.manager = PackageManager()
        self.packages = self.manager.list_packages(unpacked_only=True)
        if not self.packages:
            show_error('There are no packages available to be packaged')
            return
        self.window.show_quick_panel(self.packages, self.on_done)

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
            self.do_create_package()
            return

        self.profiles = ['Default']
        for key in rules.keys():
            self.profiles.append(key)

        def show_panel():
            self.window.show_quick_panel(self.profiles, self.on_done_profile)
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

        self.do_create_package()

    def do_create_package(self):
        """
        Calls into the PackageManager to actually create the package file
        """

        destination = self.get_package_destination()
        if self.manager.create_package(self.package_name, destination,
                profile=self.profile):
            self.window.run_command('open_dir', {"dir":
                destination, "file": self.package_name +
                '.sublime-package'})

    def get_package_destination(self):
        """
        Retrieves the destination for .sublime-package files

        :return:
            A string - the path to the folder to save .sublime-package files in
        """

        destination = None
        if self.profile:
            profiles = self.manager.settings.get('package_profiles', {})
            if self.profile in profiles:
                profile_settings = profiles[self.profile]
                destination = profile_settings.get('package_destination')

        if not destination:
            destination = self.manager.settings.get('package_destination')

        # We check destination via an if statement instead of using
        # the dict.get() method since the key may be set, but to a blank value
        if not destination:
            destination = os.path.join(os.path.expanduser('~'), 'Desktop')

        return destination
