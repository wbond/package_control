import sublime
import sublime_plugin

from ..settings import pc_settings_filename


class PackageControlEnableDebugModeCommand(sublime_plugin.WindowCommand):
    def run(self):
        settings_file = pc_settings_filename()
        settings = sublime.load_settings(settings_file)
        settings.set('debug', True)
        sublime.save_settings(settings_file)

        sublime.message_dialog(
            'Package Control\n\n'
            'Debug mode has been enabled, a log of commands will be written '
            'to the Sublime Text console'
        )

    def is_visible(self):
        return not sublime.load_settings(pc_settings_filename()).get('debug', False)

    def is_enabled(self):
        return self.is_visible()
