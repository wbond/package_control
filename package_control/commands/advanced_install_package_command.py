import threading
import time

import sublime_plugin

from ..package_disabler import PackageDisabler
from ..package_manager import PackageManager
from ..show_error import show_error
from ..thread_progress import ThreadProgress


class AdvancedInstallPackageCommand(sublime_plugin.WindowCommand):

    """
    A command that accepts a comma-separated list of packages to install, or
    prompts the user to paste a comma-separated list
    """

    def run(self, packages=None):
        if packages:
            if isinstance(packages, str):
                packages = self.split(packages)

            if isinstance(packages, list):
                thread = AdvancedInstallPackageThread(packages)
                thread.start()
                message = 'Installing package'
                if len(packages) > 1:
                    message += 's'
                ThreadProgress(thread, message, '')
                return

        self.window.show_input_panel(
            'Packages to Install (Comma-separated)',
            '',
            self.on_done,
            None,
            None
        )

    def on_done(self, input_text):
        """
        Input panel handler - adds the provided URL as a repository

        :param input_text:
            A string of the URL to the new repository
        """

        packages = self.split(input_text.strip())
        if not packages:
            show_error('No package names were entered')
            return

        self.run(packages)

    @staticmethod
    def split(packages):
        return [package.strip() for package in packages.split(',') if package]


class AdvancedInstallPackageThread(threading.Thread, PackageDisabler):

    """
    A thread to run the installation of one or more packages in
    """

    def __init__(self, packages):
        """
        :param packages:
            The string package name, or an array of strings
        """

        if isinstance(packages, str):
            packages = [packages]
        if not isinstance(packages, list):
            raise TypeError("Parameter 'packages' must be string or list!")
        self.packages = packages

        self.manager = PackageManager()
        threading.Thread.__init__(self)

    def run(self):
        installed = self.manager.list_packages()

        operations = {
            'install': [
                package for package in self.packages
                if package not in installed
            ],
            'upgrade': [
                package for package in self.packages
                if package in installed
            ]
        }

        disabled = {
            operation: self.disable_packages(packages, operation)
            for operation, packages in operations.items()
        }

        try:
            # Allow packages to properly disable
            time.sleep(0.7)

            for operation, packages in operations.items():
                for package in packages:
                    result = self.manager.install_package(package)
                    # do not re-enable package if operation is dereffered to next start
                    if result is None and package in disabled[operation]:
                        disabled[operation].remove(package)

        finally:
            time.sleep(0.7)
            for operation, packages in disabled.items():
                self.reenable_packages(packages, operation)
