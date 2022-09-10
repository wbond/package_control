import time
import threading

import sublime
import sublime_plugin

from ..package_installer import PackageInstaller, PackageInstallerThread
from ..package_renamer import PackageRenamer
from ..thread_progress import ThreadProgress

USE_QUICK_PANEL_ITEM = hasattr(sublime, 'QuickPanelItem')


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
        package_list = self.make_package_list(['install', 'reinstall', 'none'])

        if USE_QUICK_PANEL_ITEM:
            package_names = [info.trigger for info in package_list]
        else:
            package_names = [info[0] for info in package_list]

        def do_upgrade():
            disabled_packages = self.disable_packages(package_names, 'upgrade')

            try:
                # Pause so packages can be disabled
                time.sleep(0.7)

                for package_name in package_names:
                    thread = PackageInstallerThread(self.manager, package_name, None)
                    thread.start()
                    ThreadProgress(
                        thread,
                        'Upgrading package %s' % package_name,
                        'Package %s successfully upgraded' % package_name
                    )
                    thread.join()

            finally:
                time.sleep(0.7)
                self.reenable_packages(disabled_packages, 'upgrade')

        # clear "Loading repository" thread progress
        threading.Thread(target=do_upgrade).start()
