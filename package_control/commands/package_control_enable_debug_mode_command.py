import sublime
import sublime_plugin

from ..settings import pc_settings_filename
from ..show_error import show_message


class PackageControlEnableDebugModeCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        settings_file = pc_settings_filename()
        settings = sublime.load_settings(settings_file)
        settings.set('debug', True)
        sublime.save_settings(settings_file)

        show_message(
            '''
            Debug mode has been enabled, a log of commands will be written
            to the Sublime Text console
            '''
        )

    def is_visible(self):
        return not sublime.load_settings(pc_settings_filename()).get('debug', False)

    def is_enabled(self):
        return self.is_visible()
