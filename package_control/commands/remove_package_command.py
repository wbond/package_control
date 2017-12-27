import threading
import time

import sublime_plugin

from ..package_disabler import PackageDisabler
from ..show_error import show_message
from ..show_quick_panel import show_quick_panel
from ..thread_progress import ThreadProgress
from .existing_packages_command import ExistingPackagesCommand


class RemovePackageCommand(sublime_plugin.WindowCommand):

    """
    A command that presents a list of installed packages, allowing the user to
    select one to remove
    """

    def run(self):
        ListRemovePackageThread(self.window).start()


class ListRemovePackageThread(threading.Thread, ExistingPackagesCommand):

    """
    A thread to prevent the listing of existing packages from freezing the UI
    """

    def __init__(self, window):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of installed packages in.
        """

        self.window = window
        self.package_list = None
        threading.Thread.__init__(self)
        ExistingPackagesCommand.__init__(self)

    def run(self):
        self.package_list = self.make_package_list('remove')
        if not self.package_list:
            show_message('There are no packages that can be removed')
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
        package = self.package_list[picked][0]

        thread = RemovePackageThread(self.manager, package)
        thread.start()
        ThreadProgress(
            thread,
            'Removing package %s' % package,
            'Package %s successfully removed' % package
        )


class RemovePackageThread(threading.Thread, PackageDisabler):

    """
    A thread to run the remove package operation without freezing Sublime Text UI.
    """

    def __init__(self, manager, package):
        self.manager = manager
        self.package = package
        threading.Thread.__init__(self)

    def run(self):
        self.disable_packages(self.package, 'remove')

        # Let the package disabling take place
        time.sleep(0.7)

        result = self.manager.remove_package(self.package)

        # Do not reenable if removing deferred until next restart
        if result is not None:
            self.reenable_package(self.package, 'remove')
