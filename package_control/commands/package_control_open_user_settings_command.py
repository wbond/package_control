import sublime
import sublime_plugin


class PackageControlOpenUserSettingsCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command(
            'open_file',
            {
                "file": "${packages}/User/Package Control.sublime-settings",
                "contents":
                    "// See Preferences > Package Settings > Package Control > Settings - Default\n"
                    "// for the list of settings and valid values\n"
                    "{\n"
                    "\t$0\n"
                    "}\n"
            }
        )

    def is_visible(self):
        return int(sublime.version()) < 3116

    def is_enabled(self):
        return self.is_visible()
