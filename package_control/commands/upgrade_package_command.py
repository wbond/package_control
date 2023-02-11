import threading
import time

import sublime
import sublime_plugin

from ..activity_indicator import ActivityIndicator
from ..package_installer import PackageInstaller, USE_QUICK_PANEL_ITEM
from ..show_error import show_message


class UpgradePackageCommand(sublime_plugin.ApplicationCommand):

    """
    A command that presents the list of installed packages that can be upgraded
    """

    def run(self):
        UpgradePackageThread().start()


class UpgradePackageThread(threading.Thread, PackageInstaller):

    """
    A thread to run the action of retrieving upgradable packages in.
    """

    def __init__(self):
        """
        Constructs a new instance.
        """

        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        """
        Load and display a list of packages available for upgrade
        """

        with ActivityIndicator('Loading repository...'):
            package_list = self.make_package_list(actions=(self.PULL, self.UPGRADE))
            if not package_list:
                show_message('There are no packages ready for upgrade')
                return

        def on_done(picked):
            if picked == -1:
                return

            if USE_QUICK_PANEL_ITEM:
                package_name = package_list[picked].trigger
            else:
                package_name = package_list[picked][0]

            threading.Thread(target=self.upgrade, args=[package_name]).start()

        sublime.active_window().show_quick_panel(
            package_list,
            on_done,
            sublime.KEEP_OPEN_ON_FOCUS_LOST
        )

    def upgrade(self, package_name):
        """
        Upgrade selected package

        :param package_name:
            The name of the package to upgrade
        """

        result = False

        with ActivityIndicator('Upgrading package %s' % package_name) as progress:
            self.disable_packages({self.UPGRADE: package_name})
            time.sleep(0.7)

            try:
                result = self.manager.install_package(package_name)
                if result is True:
                    progress.finish('Package %s successfully upgraded' % package_name)

            finally:
                # Do not reenable if deferred until next restart
                if result is not None:
                    time.sleep(0.7)
                    self.reenable_packages({self.UPGRADE: package_name})
