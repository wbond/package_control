import sublime
import sublime_plugin

from ..show_error import show_error
from ..preferences_filename import preferences_filename


class EnablePackageCommand(sublime_plugin.WindowCommand):
    """
    A command that removes a package from Sublime Text's ignored packages list
    """

    def run(self):
        self.settings = sublime.load_settings(preferences_filename())
        self.disabled_packages = self.settings.get('ignored_packages')
        self.disabled_packages.sort()
        if not self.disabled_packages:
            show_error('There are no disabled packages to enable.')
            return
        self.window.show_quick_panel(self.disabled_packages, self.on_done)

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
        ignored = self.settings.get('ignored_packages')
        self.settings.set('ignored_packages',
            list(set(ignored) - set([package])))
        sublime.save_settings(preferences_filename())
        sublime.status_message(('Package %s successfully removed from list ' +
            'of disabled packages - restarting Sublime Text may be required') %
            package)
