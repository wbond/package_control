import unittest

from ..package_version import PackageVersion, PEP440Version
from ._data_decorator import data_decorator, data


@data_decorator
class PackageVersionTests(unittest.TestCase):
    @data(
        (
            ("1.0.0", "1"),
            ("1.0.0", "1.0"),
            ("1.2.0", "1.2"),
            ("1.0.0", "1.0.0"),
            ("1.0.0", "1.0.0.0"),
            ("1.2.3.4", "1.2.3.4"),
            # pep440 compliant pre-releases
            ("1.2.3-rc1", "1.2.3-rc1"),
            # pep440 incompatible semver releases
            ("1.2.3-dev", "1.2.3-development"),
            ("1.2.3-pre", "1.2.3-prerelease"),
            ("1.4.1-dev+foo", "1.4.1-foo"),
            ("1.4.1-dev+anypre.5", "1.4.1-anypre.5"),
            # convert datebased release to pep440 local version
            ("0.0.1+2020.07.15.10.50.38", "2020.07.15.10.50.38"),
        )
    )
    def equal(self, a, b):
        va = PEP440Version(a)
        vb = PackageVersion(b)
        self.assertEqual(va, vb)

    @data(
        (
            ("1.0.0-rc10", "1.0.0-rc9"),
            ("1.0.0-rc1", "1.0.0-beta29"),
            ("1.0.0-dev20", "1.0.0-dev2"),
            ("1.0.0-dev.200", "1.0.0-dev.20"),
            ("1.0.0", "1.0.0-pre"),
            ("1.0.0-rev1", "1.0.0"),
        )
    )
    def greater(self, a, b):
        va = PEP440Version(a)
        vb = PackageVersion(b)
        self.assertGreater(va, vb)

    def test_invalid_number(self):
        with self.assertRaises(TypeError) as cm:
            PackageVersion(1.2)
        self.assertEqual("1.2 is not a string", str(cm.exception))

    def test_invalid_string(self):
        with self.assertRaises(ValueError) as cm:
            PackageVersion("foo")
        self.assertEqual("'foo' is not a valid PEP440 version string", str(cm.exception))

    def test_strip_v_prefix(self):
        va = PackageVersion("v2020.07.15.10.50.38")
        self.assertEqual(str(va), "2020.07.15.10.50.38")
