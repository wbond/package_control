import threading

import sublime
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
            UpgradePackagesThread(packages, unattended).start()
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


class UpgradePackagesThread(threading.Thread, PackageTaskRunner):

    """
    A thread to run the installation of one or more packages in
    """

    def __init__(self, packages, unattended):
        """
        Constructs a new instance.

        :param packages:
            The list of package names to upgrade.
            If `None` all packages are upgraded.

        :param unattended:
            A flag to decide whether to display modal error/message dialogs.
        """

        self.packages = set(packages) if packages else None
        self.unattended = unattended

        threading.Thread.__init__(self)
        PackageTaskRunner.__init__(self)

    def run(self):
        message = 'Loading repository...'
        with ActivityIndicator(message) as progress:
            console_write(message)
            self.upgrade_packages(self.packages, None, self.unattended, progress)
