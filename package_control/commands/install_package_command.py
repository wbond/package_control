import sublime
import sublime_aio
import sublime_plugin

from ..activity_indicator import ActivityIndicator
from ..console_write import console_write
from ..package_tasks import PackageTaskRunner
from ..show_error import show_message


class InstallPackageCommand(sublime_aio.ApplicationCommand):

    """
    A command that presents the list of available packages and allows the
    user to pick one to install.
    """

    async def run(self):

        installer = PackageTaskRunner()

        with ActivityIndicator('Loading packages...') as progress:
            tasks = await installer.create_package_tasks(actions=(installer.INSTALL, installer.OVERWRITE))
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
            if picked == -1:
                return

            async def worker(task):
                with ActivityIndicator('Installing package %s' % task.package_name) as progress:
                    await installer.run_install_tasks([task], progress)

            sublime_aio.run_coroutine(worker(tasks[picked]))

        sublime.active_window().show_quick_panel(
            installer.render_quick_panel_items(tasks),
            on_done,
            sublime.KEEP_OPEN_ON_FOCUS_LOST
        )
