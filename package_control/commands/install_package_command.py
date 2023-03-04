import threading

import sublime
import sublime_plugin

from ..activity_indicator import ActivityIndicator
from ..console_write import console_write
from ..package_tasks import PackageTaskRunner
from ..show_error import show_message


class InstallPackageCommand(sublime_plugin.ApplicationCommand):

    """
    A command that presents the list of available packages and allows the
    user to pick one to install.
    """

    def run(self):
        InstallPackageThread().start()


class InstallPackageThread(threading.Thread, PackageTaskRunner):

    """
    A thread to run the action of retrieving available packages in. Uses the
    default PackageTaskRunner.on_done quick panel handler.
    """

    def __init__(self):
        """
        Constructs a new instance.
        """

        threading.Thread.__init__(self)
        PackageTaskRunner.__init__(self)

    def run(self):
        """
        Load and display a list of packages available for install
        """

        with ActivityIndicator('Loading repository...') as progress:
            tasks = self.create_package_tasks(actions=(self.INSTALL, self.OVERWRITE))
            if not tasks:
                message = 'There are no packages available for installation'
                console_write(message)
                progress.finish(message)
                show_message(
                    '''
                    %s

                    Please see https://packagecontrol.io/docs/troubleshooting for help
                    ''',
                    message
                )
                return

        def on_done(picked):
            if picked > -1:
                threading.Thread(target=self.install, args=[tasks[picked]]).start()

        sublime.active_window().show_quick_panel(
            self.render_quick_panel_items(tasks),
            on_done,
            sublime.KEEP_OPEN_ON_FOCUS_LOST
        )

    def install(self, task):
        """
        Install selected package

        :param task:
            The ``PackageInstallTask`` object for the package to install
        """

        with ActivityIndicator('Installing package %s' % task.package_name) as progress:
            self.run_install_tasks([task], progress)
