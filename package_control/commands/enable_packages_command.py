import sublime
import sublime_plugin

from ..package_disabler import PackageDisabler
from ..show_error import show_error


class EnablePackagesCommand(sublime_plugin.ApplicationCommand):

    """
    A command that accepts a list of packages to enable,
    or prompts the user to paste a comma-separated list.

    Example:

    ```py
    sublime.run_command("enable_packages", {"packages": ["Package 1", "Package 2"]})
    ```
    """

    def run(self, packages=None):
        if isinstance(packages, list):
            PackageDisabler.reenable_packages(packages, 'enable')
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
            sublime.status_message('Packages have been enabled.')

        sublime.active_window().show_input_panel(
            'Packages to enable (comma-separated)',
            '',
            on_done,
            None,
            None
        )
