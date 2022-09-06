import threading
import time

import sublime
import sublime_plugin

from .. import text
from ..package_disabler import PackageDisabler
from ..show_quick_panel import show_quick_panel
from ..thread_progress import ThreadProgress
from .existing_packages_command import ExistingPackagesCommand

USE_QUICK_PANEL_ITEM = hasattr(sublime, 'QuickPanelItem')


class RemovePackageCommand(sublime_plugin.WindowCommand, ExistingPackagesCommand):

    """
    A command that presents a list of installed packages, allowing the user to
    select one to remove
    """

    def __init__(self, window):
        """
        Constructs a new instance.

        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of installed packages in.
        """

        sublime_plugin.WindowCommand.__init__(self, window)
        ExistingPackagesCommand.__init__(self)

    def run(self):
        self.package_list = self.make_package_list('remove')
        if not self.package_list:
            sublime.message_dialog(text.format(
                '''
                Package Control

                There are no packages that can be removed
                '''
            ))
            return
        show_quick_panel(self.window, self.package_list, self.on_done)

    def on_done(self, picked):
        """
        Quick panel user selection handler - deletes the selected package

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return

        if USE_QUICK_PANEL_ITEM:
            package_name = self.package_list[picked].trigger
        else:
            package_name = self.package_list[picked][0]

        thread = RemovePackageThread(self.manager, package_name)
        thread.start()
        ThreadProgress(
            thread,
            'Removing package %s' % package_name,
            'Package %s successfully removed' % package_name
        )


class RemovePackageThread(threading.Thread, PackageDisabler):

    """
    A thread to run the remove package operation in so that the Sublime Text
    UI does not become frozen
    """

    def __init__(self, manager, package):
        self.result = None
        self.manager = manager
        self.package = package
        threading.Thread.__init__(self)

    def run(self):
        self.disable_packages(self.package, 'remove')

        try:
            # Let the package disabling take place
            time.sleep(0.7)
            self.result = self.manager.remove_package(self.package)
        finally:
            # Do not reenable if removing deferred until next restart
            if self.result is not None:
                time.sleep(0.7)
                self.reenable_packages(self.package, 'remove')
