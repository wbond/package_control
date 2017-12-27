import os
import threading

import sublime_plugin

from ..package_manager import PackageManager
from ..show_error import show_error
from ..show_quick_panel import show_quick_panel
from ..thread_progress import ThreadProgress


class CreatePackageCommand(sublime_plugin.WindowCommand):

    """
    Command to create a regular .sublime-package file
    """

    def run(self):
        CreatePackageWorker(self.window).start()


class CreatePackageWorker(object):

    """
    A thread to prevent the listing of existing packages from freezing the UI
    and finally create the .sublime-package file from the selected folder.
    """

    def __init__(self, window):
        self.window = window
        self.manager = PackageManager()
        self.packages = None
        self.package_name = None
        self.profiles = None
        self.profile_name = None

    def start(self):
        """
        The threading.Thread API compatible entry point to start the command.
        """

        self.show_package_name_panel()

    def show_package_name_panel(self):
        """
        Show a quick panel to select a package name from.
        """

        self.packages = self.manager.list_packages(unpacked_only=True)
        if not self.packages:
            show_error('There are no packages available to be packaged')
            return
        show_quick_panel(self.window, self.packages, self.on_package_name_done)

    def on_package_name_done(self, picked):
        """
        Quick panel user selection handler - processes the user package
        selection and prompts the user to pick a profile, or just creates the
        package file if there are no profiles

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return

        self.package_name = self.packages[picked]
        self.show_profile_name_panel()

    def show_profile_name_panel(self):
        """
        Show a quick panel to select an profile name from.
        """

        rules = self.manager.settings.get('package_profiles')
        if not rules:
            self.create_package()
            return

        self.profiles = ['Default'] + list(rules.keys())
        show_quick_panel(self.window, self.profiles, self.on_profile_done)

    def on_profile_done(self, picked):
        """
        Quick panel user selection handler - processes the package profile
        selection and creates the package file

        :param picked:
            An integer of the 0-based profile name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return

        self.profile_name = self.profiles[picked] if picked > 0 else None
        self.create_package()

    def create_package(self):
        """
        Create a thread to create the package and an activity indicator.
        """

        thread = threading.Thread(target=self.do_create_package)
        thread.start()
        ThreadProgress(
            thread,
            'Creating package %s' % self.package_name,
            'Package %s successfully created' % self.package_name
        )

    def do_create_package(self):
        """
        Calls into the PackageManager to actually create the package file
        """

        destination = self.get_package_destination()
        if self.manager.create_package(self.package_name, destination, self.profile_name):
            self.window.run_command(
                'open_dir',
                {
                    "dir": destination,
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
        if self.profile_name:
            profiles = self.manager.settings.get('package_profiles', {})
            destination = profiles.get(self.profile_name, {}).get('package_destination')

        if not destination:
            destination = self.manager.settings.get('package_destination')

        # We check destination via an if statement instead of using
        # the dict.get() method since the key may be set, but to a blank value
        if not destination:
            destination = os.path.join(os.path.expanduser('~'), 'Desktop')

        return destination
