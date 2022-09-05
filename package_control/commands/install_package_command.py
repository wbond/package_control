import threading
import time

import sublime
import sublime_plugin

from ..activity_indicator import ActivityIndicator
from ..package_installer import PackageInstaller
from ..show_error import show_message

USE_QUICK_PANEL_ITEM = hasattr(sublime, 'QuickPanelItem')


class InstallPackageCommand(sublime_plugin.ApplicationCommand):

    """
    A command that presents the list of available packages and allows the
    user to pick one to install.
    """

    def run(self):
        InstallPackageThread().start()


class InstallPackageThread(threading.Thread, PackageInstaller):

    """
    A thread to run the action of retrieving available packages in. Uses the
    default PackageInstaller.on_done quick panel handler.
    """

    def __init__(self):
        """
        Constructs a new instance.
        """

        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        """
        Load and display a list of packages available for install
        """

        with ActivityIndicator('Loading repository...'):
            package_list = self.make_package_list(['upgrade', 'downgrade', 'reinstall', 'pull', 'none'])
            if not package_list:
                show_message(
                    '''
                    There are no packages available for installation

                    Please see https://packagecontrol.io/docs/troubleshooting for help
                    '''
                )
                return

        def on_done(picked):
            if picked == -1:
                return

            if USE_QUICK_PANEL_ITEM:
                package_name = package_list[picked].trigger
            else:
                package_name = package_list[picked][0]

            threading.Thread(target=self.install, args=[package_name]).start()

        sublime.active_window().show_quick_panel(
            package_list,
            on_done,
            sublime.KEEP_OPEN_ON_FOCUS_LOST
        )

    def install(self, package_name):
        """
        Install selected package

        :param package_name:
            The name of the package to install
        """

        result = False

        with ActivityIndicator('Installing package %s' % package_name) as progress:
            self.disable_packages(package_name, 'install')
            time.sleep(0.7)

            try:
                result = self.manager.install_package(package_name)
            finally:
                # Do not reenable if deferred until next restart
                if result is not None:
                    time.sleep(0.7)
                    self.reenable_packages(package_name, 'install')
                    progress.finish('Package %s successfully installed' % package_name)
