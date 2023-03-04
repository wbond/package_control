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

        def show_quick_panel():
            upgrader = PackageTaskRunner()

            with ActivityIndicator('Searching updates...') as progress:
                tasks = upgrader.create_package_tasks(
                    actions=(upgrader.PULL, upgrader.UPGRADE),
                    ignore_packages=upgrader.get_ignored_packages()  # don't upgrade disabled packages
                )
                if tasks is False:
                    message = 'There are no packages available for upgrade'
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

                if not tasks:
                    message = 'All packages up-to-date!'
                    console_write(message)
                    progress.finish(message)
                    show_message(message)
                    return

            def on_done(picked):
                if picked == -1:
                    return

                def worker(task):
                    with ActivityIndicator('Upgrading package %s' % task.package_name) as progress:
                        upgrader.run_upgrade_tasks([task], progress)

                threading.Thread(target=worker, args=[tasks[picked]]).start()

            sublime.active_window().show_quick_panel(
                upgrader.render_quick_panel_items(tasks),
                on_done,
                sublime.KEEP_OPEN_ON_FOCUS_LOST
            )

        threading.Thread(target=show_quick_panel).start()
