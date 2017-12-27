import threading
import unittest

from . import clients
from . import downloaders
from . import http_cache
from . import providers


def select_and_run(window):
    tests = {
        'Clients Tests': (
            clients.BitBucketClientTests,
            clients.GitHubClientTests,
        ),

        'Downloaders Tests': (
            downloaders.CurlDownloaderTests,
            downloaders.UrlLibDownloaderTests,
            downloaders.WgetDownloaderTests,
            downloaders.WinINetDownloaderTests,
        ),

        'Http Cache Tests': (
            http_cache.HttpCacheTests,
        ),

        'Provider Tests': (
            providers.BitBucketRepositoryProviderTests,
            providers.ChannelProviderTests,
            providers.GitHubRepositoryProviderTests,
            providers.GitHubUserProviderTests,
            providers.RepositoryProviderTests,
        ),
    }
    panel_items = ['All Tests'] + sorted(tests.keys())

    def on_done(index):
        # canceled
        if index == -1:
            return
        # all tests
        elif index == 0:
            name = panel_items[index]
            run(window, name, [item for group in tests.values() for item in group])
        # run selected tests
        elif index > 0:
            name = panel_items[index]
            run(window, name, tests[name])

    window.show_quick_panel(panel_items, on_done)


def run(window, caption, test_cases):
    """
    Start a thread to run the provided unittests in.

    :param: window
        A Sublime Text window to show the output panel in.

    :param: caption
        The text to show in the initial message.

    :param: test_cases
        An iterateable object containing all the test cases to run.
    """

    def worker(window, test_cases):
        """The worker to run the unittests."""
        output = OutputPanel(window)
        output.write('Running Package Control "%s"\n\n' % caption)

        suite = unittest.TestSuite()

        loader = unittest.TestLoader()
        for test_case in test_cases:
            suite.addTest(loader.loadTestsFromTestCase(test_case))

        unittest.TextTestRunner(stream=output, verbosity=1).run(suite)

    threading.Thread(target=worker, args=(window, test_cases)).start()


class OutputPanel():

    """
    A stream to output content to a Sublime Text output panel.
    """

    NAME = 'package_control_tests'
    SETTINGS = {
        "auto_indent": False,
        "draw_indent_guides": False,
        "draw_white_space": "None",
        "gutter": False,
        "is_widget": True,
        "line_numbers": False,
        "match_brackets": False,
        "scroll_past_end": False,
        'word_wrap': True
    }

    def __init__(self, window):
        self.panel = window.create_output_panel(self.NAME)
        for key, value in self.SETTINGS.items():
            self.panel.settings().set(key, value)
        window.run_command('show_panel', {'panel': 'output.' + self.NAME})

    def write(self, data):
        self.panel.run_command('append', {'characters': data})
        self.panel.show(self.panel.size(), True)

    def get(self):
        pass

    def flush(self):
        pass
