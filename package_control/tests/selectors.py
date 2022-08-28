import unittest

from ..selectors import is_compatible_version, is_compatible_platform


class PlatformSelectorTests(unittest.TestCase):

    def test_is_compatible_platform_true(self):
        platform_selectors = ["windows-x64", "windows", "*"]
        self.assertTrue(is_compatible_platform("*", platform_selectors))
        self.assertTrue(is_compatible_platform(["*"], platform_selectors))
        self.assertTrue(is_compatible_platform(["windows"], platform_selectors))
        self.assertTrue(is_compatible_platform(["windows-x64"], platform_selectors))
        self.assertTrue(is_compatible_platform(["osx", "windows"], platform_selectors))

    def test_is_compatible_platform_false(self):
        platform_selectors = ["windows-x64", "windows", "*"]
        self.assertFalse(is_compatible_platform("linux", platform_selectors))
        self.assertFalse(is_compatible_platform(["linux"], platform_selectors))
        self.assertFalse(is_compatible_platform(["osx", "linux"], platform_selectors))
        self.assertFalse(is_compatible_platform(["windows-x86"], platform_selectors))


class VersionSelectorTests(unittest.TestCase):

    def test_version_less_than(self):
        self.assertTrue(is_compatible_version("<3176", 3175))

    def test_version_not_less_than(self):
        self.assertFalse(is_compatible_version("<3176", 3176))

    def test_version_less_or_equal_than(self):
        self.assertTrue(is_compatible_version("<=3176", 3175))
        self.assertTrue(is_compatible_version("<=3176", 3176))

    def test_version_not_less_or_equal_than(self):
        self.assertFalse(is_compatible_version("<=3176", 3177))

    def test_version_greater_than(self):
        self.assertTrue(is_compatible_version(">3176", 3177))

    def test_version_not_greater_than(self):
        self.assertFalse(is_compatible_version(">3176", 3176))

    def test_version_greater_or_equal_than(self):
        self.assertTrue(is_compatible_version(">=3176", 3176))
        self.assertTrue(is_compatible_version(">=3176", 3177))

    def test_version_not_greater_or_equal_than(self):
        self.assertFalse(is_compatible_version(">=3176", 3175))

    def test_version_range_below_lower_bound(self):
        self.assertFalse(is_compatible_version("3176 - 3211", 3175))

    def test_version_range_lower_bound(self):
        self.assertTrue(is_compatible_version("3176 - 3211", 3176))

    def test_version_range_upper_bound(self):
        self.assertTrue(is_compatible_version("3176 - 3211", 3211))

    def test_version_range_above_upper_bound(self):
        self.assertFalse(is_compatible_version("3176 - 3211", 3212))
