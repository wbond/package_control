import sublime
import sublime_plugin

from .. import tests


class PackageControlTestsCommand(sublime_plugin.WindowCommand):

    """
    A command to run the tests for Package Control
    """

    def run(self):
        tests.select_and_run(self.window)

    def is_visible(self):
        settings = sublime.load_settings('Package Control.sublime-settings')
        return settings.get('enable_tests', False)
