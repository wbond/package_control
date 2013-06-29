import os

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

    def get_package_destination(self):
        """
        Retrieves the destination for .sublime-package files

        :return:
            A string - the path to the folder to save .sublime-package files in
        """

        destination = self.manager.settings.get('package_destination')

        # We check destination via an if statement instead of using
        # the dict.get() method since the key may be set, but to a blank value
        if not destination:
            destination = os.path.join(os.path.expanduser('~'), 'Desktop')

        return destination
