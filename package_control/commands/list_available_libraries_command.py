import html
import re
import threading
from datetime import datetime

import sublime
import sublime_plugin

from ..activity_indicator import ActivityIndicator
from ..console_write import console_write
from ..package_manager import PackageManager
from ..show_error import show_message

USE_QUICK_PANEL_ITEM = hasattr(sublime, "QuickPanelItem")


class ListAvailableLibrariesCommand(sublime_plugin.ApplicationCommand):

    """
    A command that presents the list of available packages and allows the
    user to pick one to install.
    """

    def run(self):
        def show_quick_panel():
            manager = PackageManager()

            with ActivityIndicator("Loading libraries...") as progress:
                libraries = manager.list_available_libraries()
                if not libraries:
                    message = "There are no libraries available for installation"
                    console_write(message)
                    progress.finish(message)
                    show_message(
                        """
                        %s

                        Please see https://packagecontrol.io/docs/troubleshooting for help
                        """,
                        message,
                    )
                    return

            if USE_QUICK_PANEL_ITEM:
                self.show_quick_panel_st4(libraries.values())
            else:
                self.show_quick_panel_st3(libraries.values())

        threading.Thread(target=show_quick_panel).start()

    def show_quick_panel_st3(self, libraries):
        items = [
            [info["name"] + " v" + info["releases"][0]["version"], info["description"]]
            for info in libraries
        ]

        def on_done(picked):
            if picked > -1:
                sublime.set_clipboard(items[picked][0].split(" ", 1)[0])

        sublime.active_window().show_quick_panel(
            items, on_done, sublime.KEEP_OPEN_ON_FOCUS_LOST
        )

    def show_quick_panel_st4(self, libraries):
        # TODO: display supported python versions

        items = []
        for info in libraries:
            display_name = info["name"] + " v" + info["releases"][0]["version"]

            details = [html.escape(info["description"])]

            issues = html.escape(info["issues"])
            issues_display = re.sub(r"^https?://", "", issues)
            if issues_display:
                details.append(
                    'report bug: <a href="{}">{}</a>'.format(issues, issues_display)
                )

            try:
                date = info["releases"][0]["date"].split(" ", 1)[0]
                annotation = datetime.strptime(date, "%Y-%m-%d").strftime(
                    "Updated on %a %b %d, %Y"
                )
            except (IndexError, KeyError, ValueError):
                annotation = ""

            items.append(sublime.QuickPanelItem(display_name, details, annotation))

        def on_done(picked):
            if picked > -1:
                sublime.set_clipboard(items[picked].trigger.split(" ", 1)[0])

        sublime.active_window().show_quick_panel(
            items, on_done, sublime.KEEP_OPEN_ON_FOCUS_LOST
        )
