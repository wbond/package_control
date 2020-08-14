import sublime
import sublime_plugin


class PackageControlEditSettingsCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.run_command(
            'edit_settings',
            {
                "base_file": "${packages}/Package Control/Package Control.sublime-settings",
                "default":
                    "// See the left pane for the list of settings and valid values\n"
                    "{\n"
                    "\t$0\n"
                    "}\n"
            }
        )

    def is_visible(self):
        return int(sublime.version()) >= 3116

    def is_enabled(self):
        return self.is_visible()
