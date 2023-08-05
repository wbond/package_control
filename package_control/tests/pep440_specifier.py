import unittest

from ..pep440 import (
    PEP440InvalidVersionSpecifierError,
    PEP440VersionSpecifier,
    check_version,
)
from ._data_decorator import data_decorator, data


@data_decorator
class PEP440VersionSpecifierTests(unittest.TestCase):
    @data(
        (
            # Implicit equal strict
            ("1.0.0", "1", True),
            ("1.0.0", "1.0", True),
            ("1.0.0", "1.0.0", True),
            ("1.1.0", "1.0", False),
            ("1.1.0", "1.0.0", False),
            ("1.1.0+2019", "1.1.0", False),
            ("1.1.0+2019.0", "==1.1.0", False),
            # Implicit equal prefix
            ("1", "1.*", True),
            ("0.9", "1.*", False),
            ("1.0", "1.*", True),
            ("1.1", "1.*", True),
            ("1", "1.0.*", True),
            ("0.9", "1.0.*", False),
            ("1.0", "1.0.*", True),
            ("1.1", "1.0.*", False),
            ("0.9.0", "1.*", False),
            ("1.0.0", "1.*", True),
            ("1.0.1", "1.*", True),
            ("1.1.0", "1.*", True),
            ("1.9.9", "1.*", True),
            ("2.0.0", "1.*", False),
            ("0.9.0", "1.0.*", False),
            ("1.0.0", "1.0.*", True),
            ("1.0.9", "1.0.*", True),
            ("1.1.0", "1.0.*", False),
            # Dev releases aren't matched by implicit minor/patch
            ("1.0.0rc", "1", False),
            # Explicit equal strict
            ("1.0.0", "==1", True),
            ("1.0.0", "==1.0", True),
            ("1.0.0", "==1.0.0", True),
            ("1.1.0", "==1.0", False),
            ("1.1.0", "==1.0.0", False),
            ("1.1.0+2019", "==1.1.0", False),
            ("1.1.0+2019.0", "==1.1.0", False),
            # Explicit equal prefix
            ("1", "==1.*", True),
            ("0.9", "==1.*", False),
            ("1.0", "==1.*", True),
            ("1.1", "==1.*", True),
            ("1", "==1.0.*", True),
            ("0.9", "==1.0.*", False),
            ("1.0", "==1.0.*", True),
            ("1.1", "==1.0.*", False),
            ("0.9.0", "==1.*", False),
            ("1.0.0", "==1.*", True),
            ("1.0.1", "==1.*", True),
            ("1.1.0", "==1.*", True),
            ("1.9.9", "==1.*", True),
            ("2.0.0", "==1.*", False),
            ("0.9.0", "==1.0.*", False),
            ("1.0.0", "==1.0.*", True),
            ("1.0.9", "==1.0.*", True),
            ("1.1.0", "==1.0.*", False),
            # Not equal strict
            ("1.0.0", "!=1", False),
            ("1.0.0", "!=1.0", False),
            ("1.0.0", "!=1.0.0", False),
            ("2.0.0", "!=1", True),
            ("1.1.0", "!=1.0", True),
            ("1.1.0", "!=1.0.0", True),
            ("1.1.0+2019", "!=1.1.0", True),
            ("1.1.0+2019.0", "!=1.1.0", True),
            # Not equal prefix
            ("1", "!=1.*", False),
            ("0.9", "!=1.*", True),
            ("1.0", "!=1.*", False),
            ("1.1", "!=1.*", False),
            ("1", "!=1.0.*", False),
            ("0.9", "!=1.0.*", True),
            ("1.0", "!=1.0.*", False),
            ("1.1", "!=1.0.*", True),
            ("0.9.0", "!=1.*", True),
            ("1.0.0", "!=1.*", False),
            ("1.0.1", "!=1.*", False),
            ("1.1.0", "!=1.*", False),
            ("1.9.9", "!=1.*", False),
            ("2.0.0", "!=1.*", True),
            ("0.9.0", "!=1.0.*", True),
            ("1.0.0", "!=1.0.*", False),
            ("1.0.9", "!=1.0.*", False),
            ("1.1.0", "!=1.0.*", True),
            # Greater than
            ("1.0.0", ">1", False),
            ("1.0.0", ">1.0", False),
            ("1.0.0", ">1.0.0", False),
            ("1.1.0", ">1", True),
            ("1.1.0", ">1.0", True),
            ("1.1.0", ">1.0.0", True),

            # NOTE:
            # - pypackaging skips local versions, if they are no valid PEP440
            # - otherwise they are compared as normal versions
            # ! pep440.py currently ignores local versions
            # ("1.1.0+2019", ">1.1.0", True),
            # ("1.1.0+2019.0", ">1.1.0", True),

            # Greater than or equal
            ("1.0.0", ">=1", True),
            ("1.0.0", ">=1.0", True),
            ("1.0.0", ">=1.0.0", True),
            ("1.1.0", ">=1", True),
            ("1.1.0", ">=1.0", True),
            ("1.1.0", ">=1.0.0", True),
            ("1.1.0+2019", ">=1.1.0", True),
            ("1.1.0+2019.0", ">=1.1.0", True),
            # Less than
            ("1.0.0", "<1", False),
            ("1.0.0", "<1.0", False),
            ("1.0.0", "<1.0.0", False),
            ("1.1.0", "<2", True),
            ("1.1.0", "<1.2", True),
            ("1.1.0", "<1.2.0", True),
            ("1.1.0+2019", "<1.1.0", False),
            ("1.1.0+2019.0", "<1.1.0", False),
            # Less than or equal
            ("1.0.0", "<=1", True),
            ("1.0.0", "<=1.0", True),
            ("1.0.0", "<=1.0.0", True),
            ("1.1.0", "<=2", True),
            ("1.1.0", "<=1.1", True),
            ("1.1.0", "<=1.1.0", True),
            ("1.1.0+2019", "<=1.1.0", False),
            ("1.1.0+2019.0", "<=1.1.0", False),
            # Compatible with
            ("1.9", "~=2.2", False),
            ("2", "~=2.2", False),
            ("2.1", "~=2.2", False),
            ("2.2rc", "~=2.2", False),
            ("2.2", "~=2.2", True),
            ("2.3", "~=2.2", True),
            ("3.0", "~=2.2", False),
        )
    )
    def check_version(self, version, spec, result):
        self.assertEqual(result, check_version(spec, version, True))

    @data(
        (
            # Test the equality operation
            ("2.0", "==2", True),
            ("2.0", "==2.0", True),
            ("2.0", "==2.0.0", True),

            # NOTE:
            # - pypackaging skips local versions, if they are no valid PEP440
            # - otherwise they are compared as normal versions
            # ! pep440.py currently ignores local versions
            # ("2.0+deadbeef", "==2", True),
            # ("2.0+deadbeef", "==2.0", True),
            # ("2.0+deadbeef", "==2.0.0", True),
            # ("2.0+deadbeef", "==2+deadbeef", True),
            # ("2.0+deadbeef", "==2.0+deadbeef", True),
            # ("2.0+deadbeef", "==2.0.0+deadbeef", True),
            # ("2.0+deadbeef.0", "==2.0.0+deadbeef.00", True),

            # Test the equality operation with a prefix
            ("2.dev1", "==2.*", True),
            ("2a1", "==2.*", True),
            ("2a1.post1", "==2.*", True),
            ("2b1", "==2.*", True),
            ("2b1.dev1", "==2.*", True),
            ("2c1", "==2.*", True),
            ("2c1.post1.dev1", "==2.*", True),
            ("2c1.post1.dev1", "==2.0.*", True),
            ("2rc1", "==2.*", True),
            ("2rc1", "==2.0.*", True),
            ("2", "==2.*", True),
            ("2", "==2.0.*", True),
            ("2", "==0!2.*", True),
            ("0!2", "==2.*", True),
            ("2.0", "==2.*", True),
            ("2.0.0", "==2.*", True),
            ("2.1+local.version", "==2.1.*", True),
            # Test the in-equality operation
            ("2.1", "!=2", True),
            ("2.1", "!=2.0", True),
            ("2.0.1", "!=2", True),
            ("2.0.1", "!=2.0", True),
            ("2.0.1", "!=2.0.0", True),
            ("2.0", "!=2.0+deadbeef", True),
            # Test the in-equality operation with a prefix
            ("2.0", "!=3.*", True),
            ("2.1", "!=2.0.*", True),
            # Test the greater than equal operation
            ("2.0", ">=2", True),
            ("2.0", ">=2.0", True),
            ("2.0", ">=2.0.0", True),
            ("2.0.post1", ">=2", True),
            ("2.0.post1.dev1", ">=2", True),
            ("3", ">=2", True),
            # Test the less than equal operation
            ("2.0", "<=2", True),
            ("2.0", "<=2.0", True),
            ("2.0", "<=2.0.0", True),
            ("2.0.dev1", "<=2", True),
            ("2.0a1", "<=2", True),
            ("2.0a1.dev1", "<=2", True),
            ("2.0b1", "<=2", True),
            ("2.0b1.post1", "<=2", True),
            ("2.0c1", "<=2", True),
            ("2.0c1.post1.dev1", "<=2", True),
            ("2.0rc1", "<=2", True),
            ("1", "<=2", True),
            # Test the greater than operation
            ("3", ">2", True),
            ("2.1", ">2.0", True),
            ("2.0.1", ">2", True),
            ("2.1.post1", ">2", True),
            ("2.1+local.version", ">2", True),
            # Test the less than operation
            ("1", "<2", True),
            ("2.0", "<2.1", True),
            ("2.0.dev0", "<2.1", True),
            # Test the compatibility operation
            ("1", "~=1.0", True),
            ("1.0.1", "~=1.0", True),
            ("1.1", "~=1.0", True),
            ("1.9999999", "~=1.0", True),
            ("1.1", "~=1.0a1", True),
            ("2022.01.01", "~=2022.01.01", True),
            # Test that epochs are handled sanely
            ("2!1.0", "~=2!1.0", True),
            ("2!1.0", "==2!1.*", True),
            ("2!1.0", "==2!1.0", True),
            ("2!1.0", "!=1.0", True),
            ("2!1.0.0", "==2!1.0.*", True),
            ("2!1.0.0", "==2!1.*", True),
            ("1.0", "!=2!1.0", True),
            ("1.0", "<=2!0.1", True),
            ("2!1.0", ">=2.0", True),
            ("1.0", "<2!0.1", True),
            ("2!1.0", ">2.0", True),
            # Test some normalization rules
            ("2.0.5", ">2.0dev", True),
        )
    )
    def check_version_success(self, version, spec, result):
        self.assertEqual(result, check_version(spec, version, True))

    @data(
        (
            # Test the equality operation
            ("2.1", "==2", False),
            ("2.1", "==2.0", False),
            ("2.1", "==2.0.0", False),
            ("2.0", "==2.0+deadbeef", False),
            # Test the equality operation with a prefix
            ("2.0", "==3.*", False),
            ("2.1", "==2.0.*", False),
            # Test the in-equality operation
            ("2.0", "!=2", False),
            ("2.0", "!=2.0", False),
            ("2.0", "!=2.0.0", False),

            # NOTE:
            # - pypackaging skips local versions, if they are no valid PEP440
            # - otherwise they are compared as normal versions
            # ! pep440.py currently ignores local versions
            # ("2.0+deadbeef", "!=2", False),
            # ("2.0+deadbeef", "!=2.0", False),
            # ("2.0+deadbeef", "!=2.0.0", False),
            # ("2.0+deadbeef", "!=2+deadbeef", False),
            # ("2.0+deadbeef", "!=2.0+deadbeef", False),
            # ("2.0+deadbeef", "!=2.0.0+deadbeef", False),
            # ("2.0+deadbeef.0", "!=2.0.0+deadbeef.00", False),

            # Test the in-equality operation with a prefix
            ("2.dev1", "!=2.*", False),
            ("2a1", "!=2.*", False),
            ("2a1.post1", "!=2.*", False),
            ("2b1", "!=2.*", False),
            ("2b1.dev1", "!=2.*", False),
            ("2c1", "!=2.*", False),
            ("2c1.post1.dev1", "!=2.*", False),
            ("2c1.post1.dev1", "!=2.0.*", False),
            ("2rc1", "!=2.*", False),
            ("2rc1", "!=2.0.*", False),
            ("2", "!=2.*", False),
            ("2", "!=2.0.*", False),
            ("2.0", "!=2.*", False),
            ("2.0.0", "!=2.*", False),
            # Test the greater than equal operation
            ("2.0.dev1", ">=2", False),
            ("2.0a1", ">=2", False),
            ("2.0a1.dev1", ">=2", False),
            ("2.0b1", ">=2", False),
            ("2.0b1.post1", ">=2", False),
            ("2.0c1", ">=2", False),
            ("2.0c1.post1.dev1", ">=2", False),
            ("2.0rc1", ">=2", False),
            ("1", ">=2", False),
            # Test the less than equal operation
            ("2.0.post1", "<=2", False),
            ("2.0.post1.dev1", "<=2", False),
            ("3", "<=2", False),
            # Test the greater than operation
            ("1", ">2", False),
            ("2.0.dev1", ">2", False),
            ("2.0a1", ">2", False),
            ("2.0a1.post1", ">2", False),
            ("2.0b1", ">2", False),
            ("2.0b1.dev1", ">2", False),
            ("2.0c1", ">2", False),
            ("2.0c1.post1.dev1", ">2", False),
            ("2.0rc1", ">2", False),
            ("2.0", ">2", False),
            ("2.0.post1", ">2", False),
            ("2.0.post1.dev1", ">2", False),
            ("2.0+local.version", ">2", False),
            # Test the less than operation
            ("2.0.dev1", "<2", False),
            ("2.0a1", "<2", False),
            ("2.0a1.post1", "<2", False),
            ("2.0b1", "<2", False),
            ("2.0b2.dev1", "<2", False),
            ("2.0c1", "<2", False),
            ("2.0c1.post1.dev1", "<2", False),
            ("2.0rc1", "<2", False),
            ("2.0", "<2", False),
            ("2.post1", "<2", False),
            ("2.post1.dev1", "<2", False),
            ("3", "<2", False),
            # Test the compatibility operation
            ("2.0", "~=1.0", False),
            ("1.1.0", "~=1.0.0", False),
            ("1.1.post1", "~=1.0.0", False),
            # Test that epochs are handled sanely
            ("1.0", "~=2!1.0", False),
            ("2!1.0", "~=1.0", False),
            ("2!1.0", "==1.0", False),
            ("1.0", "==2!1.0", False),
            ("2!1.0", "==1.*", False),
            ("1.0", "==2!1.*", False),
            ("2!1.0", "!=2!1.0", False),
        )
    )
    def check_version_fail(self, version, spec, result):
        self.assertEqual(result, check_version(spec, version, True))

    @data(
        (
            # Invalid operator
            ("=>2.0",),
            # Version-less specifier
            ("==",),
            # Local segment on operators which don't support them
            ("~=1.0+5",),
            (">=1.0+deadbeef",),
            ("<=1.0+abc123",),
            (">1.0+watwat",),
            ("<1.0+1.0",),
            # Prefix matching on operators which don't support them
            ("~=1.0.*",),
            (">=1.0.*",),
            ("<=1.0.*",),
            (">1.0.*",),
            ("<1.0.*",),
            # Combination of local and prefix matching on operators which do
            # support one or the other
            ("==1.0.*+5",),
            ("!=1.0.*+deadbeef",),
            # Prefix matching cannot be used with a pre-release, post-release,
            # dev or local version
            ("==2.0a1.*",),
            ("!=2.0a1.*",),
            ("==2.0.post1.*",),
            ("!=2.0.post1.*",),
            ("==2.0.dev1.*",),
            ("!=2.0.dev1.*",),
            ("==1.0+5.*",),
            ("!=1.0+deadbeef.*",),
            # Prefix matching must appear at the end
            ("==1.0.*.5",),
            # Compatible operator requires 2 digits in the release operator
            ("~=1",),
            # Cannot use a prefix matching after a .devN version
            ("==1.0.dev1.*",),
            ("!=1.0.dev1.*",),
        )
    )
    def invalid_specifier(self, spec):
        with self.assertRaises(PEP440InvalidVersionSpecifierError):
            PEP440VersionSpecifier(spec)
