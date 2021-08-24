import unittest

from .unittest_data import data_decorator, data
from ..library import PEP440Version


@data_decorator
class LibraryTests(unittest.TestCase):
    @staticmethod
    def versions_less_than():
        return (
            ('0!100.0', '1!0.1', True),
            ('1.0.0', '1.0', False),
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
