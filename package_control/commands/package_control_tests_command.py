import io
import os.path
import threading
import unittest

import sublime
import sublime_plugin

from ..settings import pc_settings_filename


class OutputPanel(io.TextIOWrapper):
    """
    A TextIO wrapper to output test results in an output panel.
    """

    def __init__(self, window):
        self.panel = window.get_output_panel("package_control_tests")
        self.panel.settings().set("word_wrap", True)
        self.panel.settings().set("scroll_past_end", False)
        window.run_command("show_panel", {"panel": "output.package_control_tests"})

    def write(self, data):
        self.panel.run_command("package_control_insert", {"string": data})

    def get(self):
        pass

    def flush(self):
        pass


class PackageControlTestsCommand(sublime_plugin.ApplicationCommand):
    """
    A command to run the tests for Package Control
    """

    HAVE_TESTS = None

    def run(self):
        def worker():
            package_root = os.path.join(sublime.packages_path(), "Package Control")

            # tests are excluded from production builds
            # so it's ok to rely on filesystem traversal
            suite = unittest.TestLoader().discover(
                pattern="test_*.py",
                start_dir=os.path.join(package_root, "package_control", "tests"),
                top_level_dir=package_root,
            )

            output = OutputPanel(sublime.active_window())
            output.write("Running Package Control Tests\n\n")

            unittest.TextTestRunner(stream=output, verbosity=1).run(suite)

        threading.Thread(target=worker).start()

    def is_visible(self):
        if self.HAVE_TESTS is None:
            self.HAVE_TESTS = os.path.exists(
                os.path.join(sublime.packages_path(), "Package Control", "package_control", "tests")
            )

        return self.HAVE_TESTS and sublime.load_settings(pc_settings_filename()).get("enable_tests", False)
