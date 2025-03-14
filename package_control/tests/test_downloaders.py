import unittest

from ..download_manager import DownloaderException
from ..download_manager import resolve_url

from ._config import USER_AGENT, DEBUG, GH_USER, GH_PASS


class ResolveUrlTests(unittest.TestCase):

    def test_match_absolute_url(self):
        self.assertEqual(
            "https://github.com/packagecontrol-test-2/package_control-tester-2",
            resolve_url(
                "https://github.com/packagecontrol-test/package_control-tester/repository.json",
                "https://github.com/packagecontrol-test-2/package_control-tester-2"
            )
        )

    def test_match_absolute_same_scheme_url(self):
        self.assertEqual(
            "https://github.com/packagecontrol-test-2/package_control-tester-2",
            resolve_url(
                "https://github.com/packagecontrol-test/package_control-tester/repository.json",
                "//github.com/packagecontrol-test-2/package_control-tester-2"
            )
        )

    def test_match_relative_sibling_url(self):
        self.assertEqual(
            "https://github.com/packagecontrol-test/package_control-tester-2",
            resolve_url(
                "https://github.com/packagecontrol-test/package_control-tester/repository.json",
                "../package_control-tester-2"
            )
        )

    def test_match_relative_child_url(self):
        self.assertEqual(
            "https://github.com/packagecontrol-test/package_control-tester/issues",
            resolve_url(
                "https://github.com/packagecontrol-test/package_control-tester/repository.json",
                "./issues"
            )
        )
