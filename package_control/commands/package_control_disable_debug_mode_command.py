import sublime
import sublime_plugin

from ..settings import pc_settings_filename
from ..show_error import show_message


class PackageControlDisableDebugModeCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        settings_file = pc_settings_filename()
        settings = sublime.load_settings(settings_file)
        settings.set('debug', False)
        sublime.save_settings(settings_file)

        show_message('Debug mode has been disabled')

    def is_visible(self):
        return sublime.load_settings(pc_settings_filename()).get('debug', False)

    def is_enabled(self):
        return self.is_visible()
