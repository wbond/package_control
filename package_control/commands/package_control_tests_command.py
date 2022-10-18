import sublime
import sublime_plugin

from ..settings import pc_settings_filename
from ..tests import TestRunner, TEST_CLASSES


class PackageControlTestsCommand(sublime_plugin.ApplicationCommand):
    """
    A command to run the tests for Package Control
    """

    def run(self):
        TestRunner(args=(sublime.active_window(), TEST_CLASSES)).start()

    def is_visible(self):
        return sublime.load_settings(pc_settings_filename()).get('enable_tests', False)
