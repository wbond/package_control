import threading

import sublime
import sublime_plugin

from ..activity_indicator import ActivityIndicator
from ..console_write import console_write
from ..package_tasks import PackageTaskRunner
from ..show_error import show_message


class UpgradePackageCommand(sublime_plugin.ApplicationCommand):

    """
    A command that presents the list of installed packages that can be upgraded
    """

    def run(self):
        UpgradePackageThread().start()


class UpgradePackageThread(threading.Thread, PackageTaskRunner):

    """
    A thread to run the action of retrieving upgradable packages in.
    """

    def __init__(self):
        """
        Constructs a new instance.
        """

        threading.Thread.__init__(self)
        PackageTaskRunner.__init__(self)

    def run(self):
        """
        Load and display a list of packages available for upgrade
        """

        with ActivityIndicator('Loading repository...') as progress:
            tasks = self.create_package_tasks(
                actions=(self.PULL, self.UPGRADE),
                ignore_packages=self.get_ignored_packages()  # don't upgrade disabled packages
            )
            if not tasks:
                message = 'There are no packages ready for upgrade'
                console_write(message)
                progress.finish(message)
                show_message(message)
                return

        def on_done(picked):
            if picked > -1:
                threading.Thread(target=self.upgrade, args=[tasks[picked]]).start()

        sublime.active_window().show_quick_panel(
            self.render_quick_panel_items(tasks),
            on_done,
            sublime.KEEP_OPEN_ON_FOCUS_LOST
        )

    def upgrade(self, task):
        """
        Upgrade selected package

        :param task:
            The ``PackageInstallTask`` object for the package to upgrade
        """

        with ActivityIndicator('Upgrading package %s' % task.package_name) as progress:
            self.run_upgrade_tasks([task], progress)
