import sublime
import sublime_plugin


class PackageControlDisableDebugModeCommand(sublime_plugin.WindowCommand):
    def run(self):
        settings = sublime.load_settings('Package Control.sublime-settings')
        settings.set('debug', False)
        sublime.save_settings('Package Control.sublime-settings')

        sublime.message_dialog(
            'Package Control\n\n'
            'Debug mode has been disabled'
        )

    def is_visible(self):
        return sublime.load_settings('Package Control.sublime-settings').get('debug')

    def is_enabled(self):
        return self.is_visible()
