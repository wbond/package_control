import threading
import time

import sublime
import sublime_plugin

from ..package_disabler import PackageDisabler
from ..show_error import show_message
from ..show_quick_panel import show_quick_panel
from ..thread_progress import ThreadProgress
from .existing_packages_command import ExistingPackagesCommand


class RemovePackageCommand(sublime_plugin.WindowCommand, ExistingPackagesCommand, PackageDisabler):

    """
    A command that presents a list of installed packages, allowing the user to
    select one to remove
    """

    def __init__(self, window):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of installed packages in.
        """

        sublime_plugin.WindowCommand.__init__(self, window)
        ExistingPackagesCommand.__init__(self)
        self.package_list = None

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

        self.disable_packages(package, 'remove')

        thread = RemovePackageThread(self.manager, package)
        thread.start()
        ThreadProgress(
            thread,
            'Removing package %s' % package,
            'Package %s successfully removed' % package
        )


class RemovePackageThread(threading.Thread, PackageDisabler):

    """
    A thread to run the remove package operation in so that the Sublime Text
    UI does not become frozen
    """

    def __init__(self, manager, package):
        self.manager = manager
        self.package = package
        threading.Thread.__init__(self)

    def run(self):
        # Let the package disabling take place
        time.sleep(0.7)
        self.result = self.manager.remove_package(self.package)

        # Do not reenable if removing deferred until next restart
        if self.result is not None:
            def unignore_package():
                self.reenable_package(self.package, 'remove')

            sublime.set_timeout(unignore_package, 200)
