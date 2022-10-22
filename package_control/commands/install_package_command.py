import threading

import sublime
import sublime_plugin

from ..package_installer import PackageInstaller
from ..package_installer import PackageInstallerThread
from ..show_error import show_message
from ..thread_progress import ThreadProgress

USE_QUICK_PANEL_ITEM = hasattr(sublime, 'QuickPanelItem')


class InstallPackageCommand(sublime_plugin.ApplicationCommand):

    """
    A command that presents the list of available packages and allows the
    user to pick one to install.
    """

    def run(self):
        thread = InstallPackageThread(sublime.active_window())
        thread.start()
        ThreadProgress(thread, 'Loading repositories', '')


class InstallPackageThread(threading.Thread, PackageInstaller):

    """
    A thread to run the action of retrieving available packages in. Uses the
    default PackageInstaller.on_done quick panel handler.
    """

    def __init__(self, window):
        """
        Constructs a new instance.

        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the available package list in.
        """

        self.window = window
        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        self.package_list = self.make_package_list(['upgrade', 'downgrade', 'reinstall', 'pull', 'none'])
        if not self.package_list:
            show_message(
                '''
                There are no packages available for installation

                Please see https://packagecontrol.io/docs/troubleshooting for help
                '''
            )
            return

        self.window.show_quick_panel(
            self.package_list,
            self.on_done,
            sublime.KEEP_OPEN_ON_FOCUS_LOST
        )

    def on_done(self, picked):
        """
        Quick panel user selection handler - disables a package, installs or
        upgrades it, then re-enables the package

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return
        if USE_QUICK_PANEL_ITEM:
            name = self.package_list[picked].trigger
        else:
            name = self.package_list[picked][0]

        if name in self.disable_packages(name, 'install'):
            def on_complete():
                self.reenable_packages(name, 'install')
        else:
            on_complete = None

        thread = PackageInstallerThread(self.manager, name, on_complete)
        thread.start()
        ThreadProgress(
            thread,
            'Installing package %s' % name,
            'Package %s successfully installed' % name
        )
