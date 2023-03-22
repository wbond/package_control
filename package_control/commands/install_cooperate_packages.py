import threading

import sublime_plugin

from ..activity_indicator import ActivityIndicator
from ..console_write import console_write
from ..package_tasks import PackageTaskRunner


class InstallCooperatePackagesCommand(sublime_plugin.ApplicationCommand):
    """
    A command to automatically install all cooperate packages.

    This command may be used by a cooperate management package/plugin,
    which manages a list of predefined packages to install for each user.

    Example:

    Create and deploy a package such as

       ``Data/Installed Packages/MyCooperation.sublime-package``

    containing a Package Control.sublime-settings with

    ```json
    {
        "cooperate_packages": [
            "My package 1",
            "My package 2"
        ]
    }
    ```

    Add a plugin.py to the package's root folder, which calls this command
    after installation or update.

    ```py
    import sublime
    from package_control import events

    def plugin_loaded():
        if events.install(__package__) or events.upgrade(__package__):
            sublime.run_command("install_cooperate_packages", {"unattended": False})
    ```
    """

    def run(self, unattended=False):

        def worker():
            installer = PackageTaskRunner()
            cooperate_packages = installer.manager.cooperate_packages()
            if not cooperate_packages:
                console_write("No cooperate packages specified to install!")
                return

            message = 'Loading packages...'
            with ActivityIndicator(message) as progress:
                console_write(message)
                installer.install_packages(cooperate_packages, unattended, progress)

        threading.Thread(target=worker).start()
