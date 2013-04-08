import threading

import sublime
import sublime_plugin

from ..show_error import show_error
from ..package_installer import PackageInstaller
from ..thread_progress import ThreadProgress


class InstallPackageCommand(sublime_plugin.WindowCommand):
    """
    A command that presents the list of available packages and allows the
    user to pick one to install.
    """

    def run(self):
        thread = InstallPackageThread(self.window)
        thread.start()
        ThreadProgress(thread, 'Loading repositories', '')


class InstallPackageThread(threading.Thread, PackageInstaller):
    """
    A thread to run the action of retrieving available packages in. Uses the
    default PackageInstaller.on_done quick panel handler.
    """

    def __init__(self, window):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the available package list in.
        """

        self.window = window
        self.completion_type = 'installed'
        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        self.package_list = self.make_package_list(['upgrade', 'downgrade',
            'reinstall', 'pull', 'none'])

        def show_quick_panel():
            if not self.package_list:
                show_error('There are no packages available for installation')
                return
            self.window.show_quick_panel(self.package_list, self.on_done)
        sublime.set_timeout(show_quick_panel, 10)
