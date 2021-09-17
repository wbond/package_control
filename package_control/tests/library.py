import unittest

from .unittest_data import data_decorator, data
from ..pep440 import PEP440Version, pep440_version_specifier


@data_decorator
class LibraryTests(unittest.TestCase):
    @staticmethod
    def versions_less_than():
        return (
            ('2019.1', '2019.2', True),
            ('2019.01', '2019.1', False),
            ('2019.1rc1', '2019.1', True),
            ('2019.1rc1', '2019.1rc2', True),
            ('2019.1b3', '2019.1rc1', True),
            ('2019.1a3', '2019.1rc1', True),
            ('2019.1a3', '2019.1b1', True),
            ('2019.1b', '2019.1b1', True),
            ('1.0.0', '1.0', False),
            # Epoch
            ('0!100.0', '1!0.1', True),
        )

    @data('versions_less_than')
    def pep440_less(self, a, b, result):
        va = PEP440Version(a)
        vb = PEP440Version(b)
        if result:
            self.assertLess(va, vb)
        else:
            self.assertGreaterEqual(va, vb)

    @staticmethod
    def versions_greater_than():
        return (
            ('2019.1', '2019.2', False),
            ('2019.01', '2019.1', False),
            ('2019.1', '2019.01', False),
            ('2019.2', '2019.01', True),
            ('2019.1rc1', '2019.1', False),
            ('2019.1rc1', '2019.1rc2', False),
            ('2019.1rc2', '2019.1rc1', True),
            ('2019.1rc', '2019.1rc1', False),
            ('2019.1a3', '2019.1rc1', False),
            ('2019.1a3', '2019.1b1', False),
            ('2019.1b', '2019.1b1', False),
            ('1.0.0', '1.0', False),
            # Epoch
            ('1!0.1', '0!100.0', True),
        )

    @data('versions_greater_than')
    def pep440_greater(self, a, b, result):
        va = PEP440Version(a)
        vb = PEP440Version(b)
        if result:
            self.assertGreater(va, vb)
        else:
            self.assertLessEqual(va, vb)

    @staticmethod
    def versions_equal():
        return (
            ('1.0.0rc', '1.0rc0', True),
            ('1.0.0', '1.0', True),
            # Epoch
            ('1!1.0', '0!1.0', False),
        )

    @data('versions_equal')
    def pep440_equal(self, a, b, result):
        va = PEP440Version(a)
        vb = PEP440Version(b)
        if result:
            self.assertEqual(va, vb)
        else:
            self.assertNotEqual(va, vb)

    @staticmethod
    def specifier():
        return (
            # Implicit equal
            ('1.0.0', '1', True),
            ('1.0.0', '1.0', True),
            ('1.0.0', '1.0.0', True),
            ('1.1.0', '1.*', True),
            ('1.1.0', '1.0', False),
            ('1.1.0', '1.0.0', False),
            # Dev releases aren't matched by implicit minor/patch
            ('1.0.0rc', '1', False),
            # Explicit equal
            ('1.0.0', '==1', True),
            ('1.0.0', '==1.0', True),
            ('1.0.0', '==1.0.0', True),
            ('1.1.0', '==1.*', True),
            ('1.1.0', '==1.0', False),
            ('1.1.0', '==1.0.0', False),
            # Not equal
            ('1.0.0', '!=1', False),
            ('1.0.0', '!=1.0', False),
            ('1.0.0', '!=1.0.0', False),
            ('2.0.0', '!=1', True),
            ('1.1.0', '!=1.*', False),
            ('1.1.0', '!=1.0', True),
            ('1.1.0', '!=1.0.0', True),
            # Greater than
            ('1.0.0', '>1', False),
            ('1.0.0', '>1.0', False),
            ('1.0.0', '>1.0.0', False),
            ('1.1.0', '>1', True),
            ('1.1.0', '>1.0', True),
            ('1.1.0', '>1.0.0', True),
            # Greater than or equal
            ('1.0.0', '>=1', True),
            ('1.0.0', '>=1.0', True),
            ('1.0.0', '>=1.0.0', True),
            ('1.1.0', '>=1', True),
            ('1.1.0', '>=1.0', True),
            ('1.1.0', '>=1.0.0', True),
            # Less than
            ('1.0.0', '<1', False),
            ('1.0.0', '<1.0', False),
            ('1.0.0', '<1.0.0', False),
            ('1.1.0', '<2', True),
            ('1.1.0', '<1.2', True),
            ('1.1.0', '<1.2.0', True),
            # Less than or equal
            ('1.0.0', '<=1', True),
            ('1.0.0', '<=1.0', True),
            ('1.0.0', '<=1.0.0', True),
            ('1.1.0', '<=2', True),
            ('1.1.0', '<=1.1', True),
            ('1.1.0', '<=1.1.0', True),
        )

    @data('specifier')
    def pep440_specifier(self, version, version_specifier, result):
        v = PEP440Version(version)
        vs = pep440_version_specifier(version_specifier)
        if result:
            self.assertEqual(True, vs.check(v))
        else:
            self.assertEqual(False, vs.check(v))
