import threading
import unittest

from . import (
    clients,
    distinfo,
    downloaders,
    package_version,
    pep440_specifier,
    pep440_version,
    pep508_marker,
    providers,
    selectors,
)


TEST_CLASSES = [
    clients.BitBucketClientTests,
    clients.GitHubClientTests,
    clients.GitLabClientTests,
    distinfo.DistinfoTests,
    downloaders.CurlDownloaderTests,
    downloaders.OscryptoDownloaderTests,
    downloaders.ResolveUrlTests,
    downloaders.UrlLibDownloaderTests,
    downloaders.WgetDownloaderTests,
    downloaders.WinINetDownloaderTests,
    package_version.PackageVersionTests,
    pep440_specifier.PEP440VersionSpecifierTests,
    pep440_version.PEP440VersionTests,
    pep508_marker.PEP508MarkerTests,
    providers.BitBucketRepositoryProviderTests,
    providers.ChannelProviderTests,
    providers.GitHubRepositoryProviderTests,
    providers.GitHubUserProviderTests,
    providers.GitLabRepositoryProviderTests,
    providers.GitLabUserProviderTests,
    providers.JsonRepositoryProviderTests,
    selectors.PlatformSelectorTests,
    selectors.VersionSelectorTests,
]


class OutputPanel:
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


class TestRunner(threading.Thread):
    """
    Runs tests in a thread and outputs the results to an output panel

    :example:
        TestRunner(args=(window, test_classes)).start()

    :param window:
        A sublime.Window object to use to display the results

    :param test_classes:
        A unittest.TestCase class, or list of classes
    """

    def run(self):
        window, test_classes = self._args

        output = OutputPanel(window)
        output.write("Running Package Control Tests\n\n")

        if not isinstance(test_classes, list) and not isinstance(test_classes, tuple):
            test_classes = [test_classes]

        suite = unittest.TestSuite()

        loader = unittest.TestLoader()
        for test_class in test_classes:
            suite.addTest(loader.loadTestsFromTestCase(test_class))

        unittest.TextTestRunner(stream=output, verbosity=1).run(suite)
