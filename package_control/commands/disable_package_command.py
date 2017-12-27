import sublime
import sublime_plugin

from ..package_disabler import PackageDisabler
from ..package_manager import PackageManager
from ..settings import load_list_setting
from ..settings import preferences_filename
from ..show_error import show_message
from ..show_error import status_message
from ..show_quick_panel import show_quick_panel


class DisablePackageCommand(sublime_plugin.WindowCommand, PackageDisabler):

    """
    A command that adds a package to Sublime Text's ignored packages list
    """

    def __init__(self, window):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of installed packages in.
        """

        sublime_plugin.WindowCommand.__init__(self, window)
        self.package_list = None

    def run(self):
        packages = PackageManager().list_all_packages()
        settings = sublime.load_settings(preferences_filename())
        ignored = load_list_setting(settings, 'ignored_packages')
        self.package_list = sorted(
            set(packages) - set(ignored), key=lambda s: s.lower())
        if not self.package_list:
            show_message('There are no enabled packages to disable')
            return
        show_quick_panel(self.window, self.package_list, self.on_done)

    def on_done(self, picked):
        """
        Quick panel user selection handler - disables the selected package

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return
        package = self.package_list[picked]

        self.disable_packages(package, 'disable')

        status_message(
            '''
            Package %s successfully added to list of disabled packages -
            restarting Sublime Text may be required
            ''',
            package
        )
