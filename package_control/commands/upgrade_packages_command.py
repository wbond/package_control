import sublime
import sublime_aio
import sublime_plugin

from ..activity_indicator import ActivityIndicator
from ..console_write import console_write
from ..package_tasks import PackageTaskRunner
from ..show_error import show_error


class UpgradePackagesCommand(sublime_plugin.ApplicationCommand):

    """
    A command that accepts a list of packages to upgrade,
    or prompts the user to paste a comma-separated list.

    Example:

    ```py
    sublime.run_command(
        "upgrade_packages",
        {
            "packages": ["Package 1", "Package 2"],
            "unattended": False  # if True, suppress error dialogs
        }
    )
    ```
    """

    def run(self, packages=None, unattended=False):
        if isinstance(packages, list):

            async def worker():
                message = 'Searching updates...'
                with ActivityIndicator(message) as progress:
                    console_write(message)
                    upgrader = PackageTaskRunner()
                    await upgrader.upgrade_packages(packages, None, unattended, progress)

            sublime_aio.run_coroutine(worker())
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

            self.run(packages, False)

        sublime.active_window().show_input_panel(
            'Packages to upgrade (comma-separated)',
            '',
            on_done,
            None,
            None
        )
