import threading

import sublime_plugin

from ..thread_progress import ThreadProgress
from ..package_installer import PackageInstaller
from ..package_renamer import PackageRenamer


class UpgradeAllPackagesCommand(sublime_plugin.WindowCommand):

    """
    A command to automatically upgrade all installed packages that are
    upgradable.
    """

    def run(self):
        thread = UpgradeAllPackagesThread(self.window)
        thread.start()
        ThreadProgress(thread, 'Loading repositories', '')


class UpgradeAllPackagesThread(threading.Thread, PackageInstaller):

    """
    A thread to run the action of retrieving upgradable packages in.
    """

    def __init__(self, window):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of upgradable packages in.
        """
        self.window = window
        self.renamer = PackageRenamer()
        self.renamer.load_settings()
        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        self.renamer.rename_packages(self)
        package_list = self.make_package_list(['install', 'reinstall', 'none'])

        package_names = [info[0] for info in package_list]
        disabled_packages = self.disable_packages(package_names, 'upgrade')

        # wait with upgrading the first package
        pause = True

        for info in package_names:
            self.upgrade(info, disabled_packages, pause).join()
            pause = False
