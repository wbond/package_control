import sublime
import sublime_plugin

from ..clear_directory import clear_directory
from ..console_write import console_write
from ..show_error import show_message
from ..sys_path import cache_path, shortpath


class ClearPackageCacheCommand(sublime_plugin.ApplicationCommand):

    """
    A command that clears out ST's Cache directory.

    Example:

    ```py
    sublime.run_command(
        "clear_package_cache",
        {
            "unattended": False  # if True, suppress error dialogs
        }
    )
    ```
    """

    def run(self, unattended=False):
        folder = cache_path()
        if not unattended and not sublime.ok_cancel_dialog(
            'Do you want to clear "{}" to reset all packages '
            "to freshly installed state?".format(shortpath(folder)),
            title="Clear Sublime Text Cache Directory?",
        ):
            return

        if not clear_directory(folder, ignore_errors=False):
            return

        msg = "Sublime Text's cache directory has been cleared!"
        console_write(msg)

        if unattended:
            return

        msg += "\n\nYou might need to restart Sublime Text for changes to take effect."
        show_message(msg)
