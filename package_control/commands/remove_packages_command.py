import threading
import time

import sublime
import sublime_plugin

from ..package_disabler import PackageDisabler
from ..package_manager import PackageManager
from ..show_error import show_error
from ..thread_progress import ThreadProgress


class RemovePackagesCommand(sublime_plugin.ApplicationCommand):

    """
    A command that accepts a list of packages to remove,
    or prompts the user to paste a comma-separated list.

    Example:

    ```py
    sublime.run_command("remove_packages", {"packages": ["Package 1", "Package 2"]})
    ```
    """

    def run(self, packages=None):
        if isinstance(packages, list):
            thread = RemovePackagesThread(packages)
            thread.start()
            message = 'Removing package'
            if len(packages) > 1:
                message += 's'
            ThreadProgress(thread, message, '')
            return

        def on_done(input_text):
            packages = []
            for package in input_text.split(','):
                if package:
                    package = package.strip()
                    if package:
                        packages.append(package)

            if not packages:
                show_error('No package names were entered')
                return

            self.run(packages)

        sublime.active_window().show_input_panel(
            'Packages to remove (comma-separated)',
            '',
            on_done,
            None,
            None
        )


class RemovePackagesThread(threading.Thread, PackageDisabler):

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
        self.packages = set(packages)

        self.manager = PackageManager()
        threading.Thread.__init__(self)

    def run(self):
        self.disable_packages(self.packages, 'remove')
        time.sleep(0.7)

        deffered = set()

        try:
            for package in self.packages:
                result = self.manager.remove_package(package)
                # do not re-enable package if operation is dereffered to next start
                if result is None:
                    deffered.add(package)
        finally:
            time.sleep(0.7)
            self.reenable_packages(self.packages - deffered, 'remove')
