import unittest

from ..pep440 import (
    PEP440InvalidVersionError,
    PEP440Version,
)
from ._data_decorator import data_decorator, data

# This list must be in the correct sorting order
VERSIONS = [
    # Implicit epoch of 0
    "1.0.dev456",
    "1.0a1",
    "1.0a2.dev456",
    "1.0a12.dev456",
    "1.0a12",
    "1.0b1.dev456",
    "1.0b2",
    "1.0b2.post345.dev456",
    "1.0b2.post345",
    "1.0b2-346",
    "1.0c1.dev456",
    "1.0c1",
    "1.0rc2",
    "1.0c3",
    "1.0",
    "1.0.post456.dev34",
    "1.0.post456",
    "1.1.dev1",
    "1.2+123abc",
    "1.2+123abc456",
    "1.2+abc",
    "1.2+abc123",
    "1.2+abc123def",
    "1.2+1234.abc",
    "1.2+123456",
    "1.2.r32+123456",
    "1.2.rev33+123456",
    # Explicit epoch of 1
    "0!9.0.0",
    "1!1.0.dev456",
    "1!1.0a1",
    "1!1.0a2.dev456",
    "1!1.0a12.dev456",
    "1!1.0a12",
    "1!1.0b1.dev456",
    "1!1.0b2",
    "1!1.0b2.post345.dev456",
    "1!1.0b2.post345",
    "1!1.0b2-346",
    "1!1.0c1.dev456",
    "1!1.0c1",
    "1!1.0rc2",
    "1!1.0c3",
    "1!1.0",
    "1!1.0.post456.dev34",
    "1!1.0.post456",
    "1!1.1.dev1",
    "1!1.2+123abc",
    "1!1.2+123abc456",
    "1!1.2+abc",
    "1!1.2+abc123",
    "1!1.2+abc123def",
    "1!1.2+1234.abc",
    "1!1.2+123456",
    "1!1.2.r32+123456",
    "1!1.2.rev33+123456",
]


@data_decorator
class PEP440VersionTests(unittest.TestCase):
    @data([(version,) for version in VERSIONS])
    def valid_versions(self, version):
        PEP440Version(version)

    @data(
        (
            # Various development release incarnations
            ("1.0dev", "1.0.dev0"),
            ("1.0.dev", "1.0.dev0"),
            ("1.0dev1", "1.0.dev1"),
            ("1.0dev", "1.0.dev0"),
            ("1.0-dev", "1.0.dev0"),
            ("1.0-dev1", "1.0.dev1"),
            ("1.0DEV", "1.0.dev0"),
            ("1.0.DEV", "1.0.dev0"),
            ("1.0DEV1", "1.0.dev1"),
            ("1.0DEV", "1.0.dev0"),
            ("1.0.DEV1", "1.0.dev1"),
            ("1.0-DEV", "1.0.dev0"),
            ("1.0-DEV1", "1.0.dev1"),
            # Various alpha incarnations
            ("1.0a", "1.0a0"),
            ("1.0.a", "1.0a0"),
            ("1.0.a1", "1.0a1"),
            ("1.0-a", "1.0a0"),
            ("1.0-a1", "1.0a1"),
            ("1.0alpha", "1.0a0"),
            ("1.0.alpha", "1.0a0"),
            ("1.0.alpha1", "1.0a1"),
            ("1.0-alpha", "1.0a0"),
            ("1.0-alpha1", "1.0a1"),
            ("1.0A", "1.0a0"),
            ("1.0.A", "1.0a0"),
            ("1.0.A1", "1.0a1"),
            ("1.0-A", "1.0a0"),
            ("1.0-A1", "1.0a1"),
            ("1.0ALPHA", "1.0a0"),
            ("1.0.ALPHA", "1.0a0"),
            ("1.0.ALPHA1", "1.0a1"),
            ("1.0-ALPHA", "1.0a0"),
            ("1.0-ALPHA1", "1.0a1"),
            # Various beta incarnations
            ("1.0b", "1.0b0"),
            ("1.0.b", "1.0b0"),
            ("1.0.b1", "1.0b1"),
            ("1.0-b", "1.0b0"),
            ("1.0-b1", "1.0b1"),
            ("1.0beta", "1.0b0"),
            ("1.0.beta", "1.0b0"),
            ("1.0.beta1", "1.0b1"),
            ("1.0-beta", "1.0b0"),
            ("1.0-beta1", "1.0b1"),
            ("1.0B", "1.0b0"),
            ("1.0.B", "1.0b0"),
            ("1.0.B1", "1.0b1"),
            ("1.0-B", "1.0b0"),
            ("1.0-B1", "1.0b1"),
            ("1.0BETA", "1.0b0"),
            ("1.0.BETA", "1.0b0"),
            ("1.0.BETA1", "1.0b1"),
            ("1.0-BETA", "1.0b0"),
            ("1.0-BETA1", "1.0b1"),
            # Various release candidate incarnations
            ("1.0c", "1.0rc0"),
            ("1.0.c", "1.0rc0"),
            ("1.0.c1", "1.0rc1"),
            ("1.0-c", "1.0rc0"),
            ("1.0-c1", "1.0rc1"),
            ("1.0rc", "1.0rc0"),
            ("1.0.rc", "1.0rc0"),
            ("1.0.rc1", "1.0rc1"),
            ("1.0-rc", "1.0rc0"),
            ("1.0-rc1", "1.0rc1"),
            ("1.0C", "1.0rc0"),
            ("1.0.C", "1.0rc0"),
            ("1.0.C1", "1.0rc1"),
            ("1.0-C", "1.0rc0"),
            ("1.0-C1", "1.0rc1"),
            ("1.0RC", "1.0rc0"),
            ("1.0.RC", "1.0rc0"),
            ("1.0.RC1", "1.0rc1"),
            ("1.0-RC", "1.0rc0"),
            ("1.0-RC1", "1.0rc1"),
            # Various post release incarnations
            ("1.0post", "1.0.post0"),
            ("1.0.post", "1.0.post0"),
            ("1.0post1", "1.0.post1"),
            ("1.0post", "1.0.post0"),
            ("1.0-post", "1.0.post0"),
            ("1.0-post1", "1.0.post1"),
            ("1.0POST", "1.0.post0"),
            ("1.0.POST", "1.0.post0"),
            ("1.0POST1", "1.0.post1"),
            ("1.0POST", "1.0.post0"),
            ("1.0r", "1.0.post0"),
            ("1.0rev", "1.0.post0"),
            ("1.0.POST1", "1.0.post1"),
            ("1.0.r1", "1.0.post1"),
            ("1.0.rev1", "1.0.post1"),
            ("1.0-POST", "1.0.post0"),
            ("1.0-POST1", "1.0.post1"),
            ("1.0-5", "1.0.post5"),
            ("1.0-r5", "1.0.post5"),
            ("1.0-rev5", "1.0.post5"),
            # Local version case insensitivity
            ("1.0+AbC", "1.0+abc"),
            # Integer Normalization
            ("1.01", "1.1"),
            ("1.0a05", "1.0a5"),
            ("1.0b07", "1.0b7"),
            ("1.0c056", "1.0rc56"),
            ("1.0rc09", "1.0rc9"),
            ("1.0.post000", "1.0.post0"),
            ("1.1.dev09000", "1.1.dev9000"),
            ("00!1.2", "1.2"),
            ("0100!0.0", "100!0.0"),
            # Various other normalizations
            ("v1.0", "1.0"),
            ("   v1.0\t\n", "1.0"),
        )
    )
    def normalized_versions(self, version, normalized):
        assert str(PEP440Version(version)) == normalized

    @data(
        (
            # Non sensical versions should be invalid
            ("french toast",),
            # Versions with invalid local versions
            ("1.0+a+",),
            ("1.0++",),
            ("1.0+_foobar",),
            ("1.0+foo&asd",),
            ("1.0+1+1",),
        )
    )
    def invalid_versions(self, version):
        with self.assertRaises(PEP440InvalidVersionError):
            PEP440Version(version)

    @data(
        (
            ("2019.2", "2019.01"),
            ("2019.1rc2", "2019.1rc1"),
            ("2019.1b1", "2019.1b1-dev"),
            ("2019.1b1-rev1", "2019.1b1-rev1-dev"),
            # Epoch
            ("1!0.1", "0!100.0"),
        )
        # compare global versions
        + tuple((v, VERSIONS[i]) for i, v in enumerate(VERSIONS[1:]))
    )
    def greater_than(self, a, b):
        va = PEP440Version(a)
        vb = PEP440Version(b)
        self.assertGreater(va, vb)

    @data(
        (
            ("2019.01", "2019.1"),
            ("2019.1b1", "2019.1b1-dev"),
            ("2019.1b1-rev1", "2019.1b1-rev1-dev"),
            ("1.0.0", "1.0"),
        )
        # compare global versions
        + tuple((v, VERSIONS[i]) for i, v in enumerate(VERSIONS[1:]))
    )
    def greater_equal_than(self, a, b):
        va = PEP440Version(a)
        vb = PEP440Version(b)
        self.assertGreaterEqual(va, vb)

    @data(
        (
            ("2019.1", "2019.2"),
            ("2019.1rc1", "2019.1"),
            ("2019.1rc1", "2019.1rc2"),
            ("2019.1b3", "2019.1rc1"),
            ("2019.1a3", "2019.1rc1"),
            ("2019.1a3", "2019.1b1"),
            ("2019.1b", "2019.1b1"),
            ("2019.1b1", "2019.1b1-rev"),
            # Epoch
            ("0!100.0", "1!0.1"),
        )
        # compare global versions
        + tuple((VERSIONS[i], v) for i, v in enumerate(VERSIONS[1:]))
    )
    def less_than(self, a, b):
        va = PEP440Version(a)
        vb = PEP440Version(b)
        self.assertLess(va, vb)

    @data(
        (
            ("2019.1", "2019.2"),
            ("2019.01", "2019.1"),
            ("2019.1", "2019.01"),
            ("2019.1rc1", "2019.1"),
            ("2019.1rc1", "2019.1rc2"),
            ("2019.1rc", "2019.1rc1"),
            ("2019.1a3", "2019.1rc1"),
            ("2019.1a3", "2019.1b1"),
            ("2019.1b", "2019.1b1"),
            ("2019.1b1", "2019.1b1-rev"),
            ("1.0.0", "1.0"),
        )
        # compare global versions
        + tuple((VERSIONS[i], v) for i, v in enumerate(VERSIONS[1:]))
    )
    def less_equal_than(self, a, b):
        va = PEP440Version(a)
        vb = PEP440Version(b)
        self.assertLessEqual(va, vb)

    @data(
        (
            ("1.0.0rc1", "1.0c1"),
            ("1.0.0rc", "1.0rc0"),
            ("1.0.0", "1.0"),
            ("1.0.0", "1"),
        )
    )
    def equal(self, a, b):
        va = PEP440Version(a)
        vb = PEP440Version(b)
        self.assertEqual(va, vb)

    @data(
        (
            ("1!1.0", "0!1.0"),
        )
        # compare global versions
        + tuple((VERSIONS[i], v) for i, v in enumerate(VERSIONS[1:]))
    )
    def not_equal(self, a, b):
        va = PEP440Version(a)
        vb = PEP440Version(b)
        self.assertNotEqual(va, vb)
