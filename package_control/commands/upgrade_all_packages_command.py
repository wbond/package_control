import threading

import sublime_plugin

from ..activity_indicator import ActivityIndicator
from ..console_write import console_write
from ..package_tasks import PackageTaskRunner


class UpgradeAllPackagesCommand(sublime_plugin.ApplicationCommand):

    """
    A command to automatically upgrade all installed packages that are
    upgradable.

    ```py
    sublime.run_command("upgrade_all_packages", {"unattended": False})
    ```
    """

    def run(self, unattended=False):

        def worker():
            message = 'Searching updates...'
            with ActivityIndicator(message) as progress:
                console_write(message)
                upgrader = PackageTaskRunner()
                upgrader.upgrade_packages(None, None, unattended, progress)

        threading.Thread(target=worker).start()
