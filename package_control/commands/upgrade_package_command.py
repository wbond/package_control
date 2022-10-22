import threading

import sublime
import sublime_plugin

from ..package_installer import PackageInstaller
from ..package_installer import PackageInstallerThread
from ..package_renamer import PackageRenamer
from ..show_error import show_message
from ..thread_progress import ThreadProgress

USE_QUICK_PANEL_ITEM = hasattr(sublime, 'QuickPanelItem')


class UpgradePackageCommand(sublime_plugin.ApplicationCommand):

    """
    A command that presents the list of installed packages that can be upgraded
    """

    def run(self):
        thread = UpgradePackageThread(sublime.active_window())
        thread.start()
        ThreadProgress(thread, 'Loading repositories', '')


class UpgradePackageThread(threading.Thread, PackageInstaller):

    """
    A thread to run the action of retrieving upgradable packages in.
    """

    def __init__(self, window):
        """
        Constructs a new instance.

        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of upgradable packages in.
        """

        self.window = window
        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        PackageRenamer().rename_packages(self.manager)

        self.package_list = self.make_package_list(['install', 'reinstall', 'none'])
        if not self.package_list:
            show_message('There are no packages ready for upgrade')
            return

        self.window.show_quick_panel(
            self.package_list,
            self.on_done,
            sublime.KEEP_OPEN_ON_FOCUS_LOST
        )

    def on_done(self, picked):
        """
        Quick panel user selection handler - disables a package, upgrades it,
        then re-enables the package

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

        if package_name in self.disable_packages(package_name, 'upgrade'):
            def on_complete():
                self.reenable_packages(package_name, 'upgrade')
        else:
            on_complete = None

        thread = PackageInstallerThread(self.manager, package_name, on_complete, pause=True)
        thread.start()
        ThreadProgress(
            thread,
            'Upgrading package %s' % package_name,
            'Package %s successfully upgraded' % package_name
        )
