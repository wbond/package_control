import threading

import sublime
import sublime_plugin

from ..activity_indicator import ActivityIndicator
from ..console_write import console_write
from ..package_tasks import PackageTaskRunner
from ..settings import (
    preferences_filename,
    load_list_setting,
)
from ..show_error import show_message


class InstallPackageCommand(sublime_plugin.ApplicationCommand):

    """
    A command that presents the list of available packages and allows the
    user to pick one to install.
    """

    def run(self):

        def show_quick_panel():
            installer = PackageTaskRunner()
            installed = installer.manager.installed_packages()
            settings = sublime.load_settings(preferences_filename())
            disabled = installed & load_list_setting(settings, 'ignored_packages')

            with ActivityIndicator('Loading packages...') as progress:
                tasks = installer.create_package_tasks(actions=(
                    installer.INSTALL, installer.OVERWRITE, installer.REINSTALL,
                    installer.UPGRADE, installer.DOWNGRADE
                )
                )
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

            for task in tasks:
                if task.action in (installer.REINSTALL, installer.UPGRADE, installer.DOWNGRADE):
                    if task.package_name in disabled:
                        task.action = installer.ENABLE

            def on_done(picked):
                if picked == -1:
                    return

                def worker(task):
                    with ActivityIndicator('Installing package %s' % task.package_name) as progress:
                        installer.run_install_tasks([task], progress)

                task = tasks[picked]
                if task.action == installer.ENABLE:
                    sublime.run_command("enable_packages", {"packages": [task.package_name]})
                else:
                    threading.Thread(target=worker, args=[task]).start()

            sublime.active_window().show_quick_panel(
                installer.render_quick_panel_items(tasks),
                on_done,
                sublime.KEEP_OPEN_ON_FOCUS_LOST
            )

        threading.Thread(target=show_quick_panel).start()
