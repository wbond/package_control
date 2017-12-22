import sublime
import sublime_plugin

from .. import text
from ..package_disabler import PackageDisabler
from ..settings import preferences_filename, load_list_setting
from ..show_quick_panel import show_quick_panel


class EnablePackageCommand(sublime_plugin.WindowCommand, PackageDisabler):

    """
    A command that removes a package from Sublime Text's ignored packages list
    """

    def __init__(self, window):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of installed packages in.
        """

        sublime_plugin.WindowCommand.__init__(self, window)
        self.disabled_packages = None

    def run(self):
        settings = sublime.load_settings(preferences_filename())
        self.disabled_packages = load_list_setting(settings, 'ignored_packages')
        if not self.disabled_packages:
            sublime.message_dialog(text.format(
                '''
                Package Control

                There are no disabled packages to enable
                '''
            ))
            return
        show_quick_panel(self.window, self.disabled_packages, self.on_done)

    def on_done(self, picked):
        """
        Quick panel user selection handler - enables the selected package

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return
        package = self.disabled_packages[picked]

        self.reenable_package(package, 'enable')

        sublime.status_message(text.format(
            '''
            Package %s successfully removed from list of disabled packages -
            restarting Sublime Text may be required
            ''',
            package
        ))
