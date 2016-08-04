import sublime
import sublime_plugin

from .. import text
from ..show_quick_panel import show_quick_panel
from ..package_manager import PackageManager
from ..settings import preferences_filename
from ..package_disabler import PackageDisabler


class DisablePackageCommand(sublime_plugin.WindowCommand, PackageDisabler):

    """
    A command that adds a package to Sublime Text's ignored packages list
    """

    def run(self):
        manager = PackageManager()
        packages = manager.list_all_packages()
        self.settings = sublime.load_settings(preferences_filename())
        ignored = self.settings.get('ignored_packages')
        if not ignored:
            ignored = []
        self.package_list = list(set(packages) - set(ignored))
        self.package_list = sorted(self.package_list, key=lambda s: s.lower())
        if not self.package_list:
            sublime.message_dialog(text.format(
                u'''
                Package Control

                There are no enabled packages to disable
                '''
            ))
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

        sublime.status_message(text.format(
            '''
            Package %s successfully added to list of disabled packages -
            restarting Sublime Text may be required
            ''',
            package
        ))
