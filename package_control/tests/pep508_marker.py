import unittest

from .. import pep508
from ..pep508 import PEP508EnvironmentMarker
from ._data_decorator import data_decorator, data


@data_decorator
class PEP508MarkerTests(unittest.TestCase):
    @data(
        (
            ('python_version == "3.8"', True),
            ("python_version == '3.8'", True),
            ("'darwin' in sys.platform", True),
            ("python_version == '3.8' and 'darwin' in sys.platform", True),
            ("'win32' in sys.platform or python_version == '3.8'", True),
            ("'darwin2' in sys.platform", False),
            ("'win32' == sys.platform", False),
        )
    )
    def pep508_environment_marker(self, markers, result):
        ORIG_MARKERS = pep508.MARKERS
        pep508.MARKERS = {
            pep508.PYTHON_VERSION: "3.8",
            pep508.PYTHON_FULL_VERSION: "3.8.10",
            pep508.OS_NAME: "posix",
            pep508.SYS_PLATFORM: "darwin",
            pep508.PLATFORM_VERSION: "Darwin Kernel Version 19.6.0",
            pep508.PLATFORM_MACHINE: "x86_64",
            pep508.PLATFORM_PYTHON_IMPLEMENTATION: "CPython",
        }

        try:
            v = PEP508EnvironmentMarker(markers)
            if result:
                self.assertEqual(True, v.check())
            else:
                self.assertEqual(False, v.check())

        finally:
            pep508.MARKERS = ORIG_MARKERS
