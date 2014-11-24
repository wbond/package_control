import sublime
import sublime_plugin

from ..show_error import show_error
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
        self.package_list.sort()
        if not self.package_list:
            show_error('There are no enabled packages to disable.')
            return
        self.window.show_quick_panel(self.package_list, self.on_done)

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

        sublime.status_message(('Package %s successfully added to list of ' +
            'disabled packages - restarting Sublime Text may be required') %
            package)
