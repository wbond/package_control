import sublime
import sublime_plugin

from ..tests import TestRunner, TEST_CLASSES


class PackageControlTestsCommand(sublime_plugin.WindowCommand):
    """
    A command to run the tests for Package Control
    """

    def run(self):
        TestRunner(args=(self.window, TEST_CLASSES)).start()

    def is_visible(self):
        settings = sublime.load_settings('Package Control.sublime-settings')
        return settings.get('enable_tests', False)
