import sublime_plugin

from .upgrade_packages_command import UpgradePackagesThread


class UpgradeAllPackagesCommand(sublime_plugin.ApplicationCommand):

    """
    A command to automatically upgrade all installed packages that are
    upgradable.

    ```py
    sublime.run_command("upgrade_all_packages", {"unattended": False})
    ```
    """

    def run(self, unattended=False):
        UpgradePackagesThread(None, unattended).start()
