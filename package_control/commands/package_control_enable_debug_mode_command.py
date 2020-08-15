import sublime
import sublime_plugin


class PackageControlEnableDebugModeCommand(sublime_plugin.WindowCommand):
    def run(self):
        settings = sublime.load_settings('Package Control.sublime-settings')
        settings.set('debug', True)
        sublime.save_settings('Package Control.sublime-settings')

        sublime.message_dialog(
            'Package Control\n\n'
            'Debug mode has been enabled, a log of commands will be written '
            'to the Sublime Text console'
        )

    def is_visible(self):
        return not sublime.load_settings('Package Control.sublime-settings').get('debug')

    def is_enabled(self):
        return self.is_visible()
