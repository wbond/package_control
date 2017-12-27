import sublime_plugin

from ..package_disabler import PackageDisabler
from ..show_error import show_message
from ..show_error import status_message
from ..show_quick_panel import show_quick_panel


class EnablePackageCommand(sublime_plugin.WindowCommand):

    """
    A command that removes a package from Sublime Text's ignored packages list
    """

    def run(self):
        EnablePackageWorker(self.window).start()


class EnablePackageWorker(PackageDisabler):

    """
    A worker to handle all temporary objects required to display a quick panel to
    list packages and remove the selected one from Sublime Text's ignored packages list
    """

    def __init__(self, window):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of installed packages in.
        """
        self.window = window
        self.package_list = None

    def start(self):
        """
        The threading.Thread API compatible entry point to start the command.
        """

        self.package_list = self.disabled_packages()
        if not self.package_list:
            show_message('There are no disabled packages to enable')
            return
        show_quick_panel(self.window, self.package_list, self.on_done)

    def on_done(self, picked):
        """
        Quick panel user selection handler - enables the selected package

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return
        package = self.package_list[picked]

        self.reenable_package(package, 'enable')

        status_message(
            '''
            Package %s successfully removed from list of disabled packages -
            restarting Sublime Text may be required
            ''',
            package
        )
