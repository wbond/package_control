import sublime
import sublime_plugin


class PackageMessageCommand(sublime_plugin.TextCommand):
    """
    A command to write a package message to the Package Control messaging buffer
    """

    def run(self, edit, string=''):
        self.view.insert(edit, self.view.size(), string)
