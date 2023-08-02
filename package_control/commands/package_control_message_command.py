import sublime
import sublime_plugin

from .. import text


class PackageControlMessageCommand(sublime_plugin.TextCommand):
    def run(self, edit, message):
        if self.view.name() != 'Package Control Messages':
            return

        old_eof = sublime.Region(self.view.size())
        old_sel = list(self.view.sel())

        self.view.set_read_only(False)

        if not old_eof.end():
            self.view.insert(edit, 0, text.format(
                '''
                Package Control Messages
                ========================
                '''
            ))
        self.view.insert(edit, self.view.size(), message)

        self.view.set_read_only(True)

        # Move caret to the new end of the file if it was previously
        if old_eof == old_sel[-1]:
            old_sel[-1] = sublime.Region(self.view.size())
            self.view.sel().clear()
            self.view.sel().add_all(old_sel)
            self.view.show(old_sel[-1], False)
