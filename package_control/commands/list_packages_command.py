import os

import sublime

from .. import package_io
from .. import sys_path
from .existing_packages_command import ExistingPackagesCommand


class ListPackagesCommand(ExistingPackagesCommand):

    """
    A command that shows a list of all installed packages in the quick panel
    """

    def action(self):
        """
        Build a strng to describe the action taken on selected package.
        """

        return "goto"

    def no_packages_error(self):
        """
        Return the error message to display if no packages are availablw.
        """

        return "There are no packages to list"

    def list_packages(self, manager):
        """
        Build a list of packages to display.

        :param manager:
            The package manager instance to use.

        :returns:
            A list of package names to add to the quick panel
        """

        return manager.list_packages()

    def on_done(self, manager, package_name):
        """
        Quick panel user selection handler - opens the homepage for any
        selected package in the user's browser

        :param manager:
            The package manager instance to use.

        :param package_name:
            A package name to perform action for
        """

        package_dir = package_io.get_package_dir(package_name)
        package_file = None

        if not os.path.exists(package_dir):
            package_path = package_io.get_installed_package_path(package_name)
            if os.path.exists(package_path):
                package_dir, package_file = os.path.split(package_path)
            else:
                package_dir = os.path.dirname(package_path)

        open_dir_file = {'dir': sys_path.shortpath(package_dir)}
        if package_file is not None:
            open_dir_file['file'] = package_file

        sublime.active_window().run_command('open_dir', open_dir_file)
