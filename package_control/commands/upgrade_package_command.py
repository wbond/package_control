import threading

import sublime
import sublime_plugin

from ..show_error import show_error
from ..thread_progress import ThreadProgress
from ..package_installer import PackageInstaller, PackageInstallerThread
from ..package_renamer import PackageRenamer


class UpgradePackageCommand(sublime_plugin.WindowCommand):
    """
    A command that presents the list of installed packages that can be upgraded
    """

    def run(self):
        package_renamer = PackageRenamer()
        package_renamer.load_settings()

        thread = UpgradePackageThread(self.window, package_renamer)
        thread.start()
        ThreadProgress(thread, 'Loading repositories', '')


class UpgradePackageThread(threading.Thread, PackageInstaller):
    """
    A thread to run the action of retrieving upgradable packages in.
    """

    def __init__(self, window, package_renamer):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of upgradable packages in.

        :param package_renamer:
            An instance of :class:`PackageRenamer`
        """
        self.window = window
        self.package_renamer = package_renamer
        self.completion_type = 'upgraded'
        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        self.package_renamer.rename_packages(self)

        self.package_list = self.make_package_list(['install', 'reinstall',
            'none'])

        def show_quick_panel():
            if not self.package_list:
                show_error('There are no packages ready for upgrade')
                return
            self.window.show_quick_panel(self.package_list, self.on_done)
        sublime.set_timeout(show_quick_panel, 10)

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
        name = self.package_list[picked][0]

        if name in self.disable_packages(name, 'upgrade'):
            on_complete = lambda: self.reenable_package(name)
        else:
            on_complete = None

        thread = PackageInstallerThread(self.manager, name, on_complete,
            pause=True)
        thread.start()
        ThreadProgress(thread, 'Upgrading package %s' % name,
            'Package %s successfully %s' % (name, self.completion_type))
