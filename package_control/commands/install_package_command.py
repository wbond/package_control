import threading

import sublime
import sublime_plugin

from .. import text
from ..show_quick_panel import show_quick_panel
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
        self.package_list = self.make_package_list(['upgrade', 'downgrade', 'reinstall', 'pull', 'none'])

        def show_panel():
            if not self.package_list:
                sublime.message_dialog(text.format(
                    u'''
                    Package Control

                    There are no packages available for installation

                    Please see https://packagecontrol.io/docs/troubleshooting
                    for help
                    '''
                ))
                return
            show_quick_panel(self.window, self.package_list, self.on_done)

        sublime.set_timeout(show_panel, 10)
