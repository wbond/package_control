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

        if not unattended:
            msg = 'Do you want to clear "{}" to reset all packages to freshly installed state?'.format(
                shortpath(folder)
            )

            # ST4 supports modal dialogs with title
            if hasattr(sublime.ok_cancel_dialog, "title") and not sublime.ok_cancel_dialog(
                msg, title="Clear Sublime Text Cache Directory?"
            ):
                return

            # ST3
            elif not sublime.ok_cancel_dialog(msg):
                return

        if not clear_directory(folder, ignore_errors=False):
            return

        msg = "Sublime Text's cache directory has been cleared!"
        console_write(msg)

        if unattended:
            return

        msg += "\n\nYou might need to restart Sublime Text for changes to take effect."
        show_message(msg)
