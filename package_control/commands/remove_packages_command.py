import threading

import sublime
import sublime_plugin

from ..activity_indicator import ActivityIndicator
from ..package_tasks import PackageTaskRunner
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

            def worker():
                with ActivityIndicator() as progress:
                    remover = PackageTaskRunner()
                    remover.remove_packages(packages, progress)

            threading.Thread(target=worker).start()
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
