import threading
import time

import sublime
import sublime_plugin

from ..activity_indicator import ActivityIndicator
from ..console_write import console_write
from ..package_disabler import PackageDisabler
from ..package_manager import PackageManager
from ..show_error import show_error


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
            RemovePackagesThread(PackageManager(), packages).start()
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

    def __init__(self, manager, packages):
        """
        :param packages:
            The string package name, or an array of strings
        """

        if isinstance(packages, str):
            packages = [packages]
        if not isinstance(packages, list):
            raise TypeError("Parameter 'packages' must be string or list!")
        self.packages = set(packages)

        self.manager = manager
        threading.Thread.__init__(self)

    def run(self):
        num_packages = len(self.packages)
        if num_packages == 1:
            message = 'Removing package %s' % list(self.packages)[0]
        else:
            message = 'Removing %d packages...' % num_packages

        with ActivityIndicator(message) as progress:

            if num_packages > 1:
                console_write(message)

            self.disable_packages({self.REMOVE: self.packages})
            time.sleep(0.7)

            deffered = set()
            num_removed = 0

            try:
                for package in sorted(self.packages, key=lambda s: s.lower()):
                    progress.set_label('Removing package %s' % package)
                    result = self.manager.remove_package(package)
                    if result is True:
                        num_removed += 1
                    # do not re-enable package if operation is dereffered to next start
                    elif result is None:
                        deffered.add(package)

                if num_packages == 1:
                    message = 'Package %s successfully removed' % list(self.packages)[0]
                elif num_packages == num_removed:
                    message = 'All packages successfully removed'
                    console_write(message)
                else:
                    message = '%d of %d packages successfully removed' % (num_removed, num_packages)
                    console_write(message)

                progress.finish(message)

            finally:
                time.sleep(0.7)
                self.reenable_packages({self.REMOVE: self.packages - deffered})
