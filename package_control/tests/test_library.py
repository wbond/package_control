import sys
import unittest

from .. import library
from ._data_decorator import data_decorator, data

PY33 = sys.version_info[:2] == (3, 3)


@data_decorator
class LibraryTests(unittest.TestCase):
    @data(
        (
            ("testlib", "testlib"),
            ("test-lib", "test_lib"),
            ("Test-liB", "Test_liB"),
            ("test_lib", "test_lib"),
            ("test.lib", "test.lib"),
            ("test.0815", "test.0815"),
            ("test!0815", "test_0815"),
            ("test?0815", "test_0815"),
            ("test=0815", "test_0815"),
        )
    )
    def escape_name(self, name, result):
        self.assertEqual(result, library.escape_name(name))

    @data(
        (
            # legacy dependencies are translated
            ("bs4", "beautifulsoup4"),
            ("dateutil", "python-dateutil"),
            ("python-jinja2", "Jinja2"),
            ("python-markdown", "Markdown"),
            ("python-pywin32", "pywin32"),
            ("python-six", "six"),
            ("python-toml", "toml"),
            ("pyyaml", "PyYAML"),
            ("ruamel-yaml", "ruamel.yaml"),
            ("serial", "pyserial"),
            # normal python packages keep unchanged
            ("Markdown", "Markdown"),
            ("markdown", "markdown"),
            ("python-docx", "python-docx"),
            ("ruamel.yaml", "ruamel.yaml"),
            # check no escaping being performed
            ("testlib", "testlib"),
            ("test-lib", "test-lib"),
            ("Test-liB", "Test-liB"),
            ("test_lib", "test_lib"),
            ("test.lib", "test.lib"),
            ("test.0815", "test.0815"),
            ("test!0815", "test!0815"),
            ("test?0815", "test?0815"),
            ("test=0815", "test=0815"),
        )
    )
    def translate_name(self, name, result):
        self.assertEqual(result, library.translate_name(name))

    @unittest.skipIf(PY33, "requires ST4 with py38")
    def test_names_to_libraries(self):
        self.assertEqual(
            [
                library.Library(n, "3.8")
                for n in ("beautifulsoup4", "python-dateutil", "python-docx")
            ],
            sorted(
                library.names_to_libraries(["bs4", "dateutil", "pathlib", "python-docx"], "3.8")
            ),
        )

    @data(
        (
            (("test-lib", "3.3"), ("test-lib", "3.3")),
            (("test-lib", "3.3"), ("test_lib", "3.3")),
            (("test-lib", "3.3"), ("Test_lib", "3.3")),
            (("test lib", "3.3"), ("test_lib", "3.3")),
            (("Test-Lib", "3.3"), ("test_lib", "3.3")),
            (("Test-Lib", "3.3"), ("test-lib", "3.3")),
            (("Test!Lib", "3.3"), ("test?lib", "3.3")),
            (("Test!Lib", "3.3"), ("test_lib", "3.3")),
        )
    )
    def library_equal(self, a, b):
        self.assertEqual(library.Library(*a), library.Library(*b))

    @data(
        (
            (("test-lib", "3.3"), ("test.lib", "3.3")),
            (("test_lib", "3.3"), ("test.lib", "3.3")),
            (("testlib", "3.3"), ("test.lib", "3.3")),
            (("testlib", "3.3"), ("test_lib", "3.3")),
            (("testlib", "3.3"), ("test-lib", "3.3")),
        )
    )
    def library_not_equal(self, a, b):
        self.assertNotEqual(library.Library(*a), library.Library(*b))

    @data(
        (
            (("test-lib-1", "3.3"), ("test-lib-2", "3.3")),
            (("test-lib-a", "3.3"), ("test-lib-b", "3.3")),
        )
    )
    def library_lesser(self, a, b):
        self.assertLess(library.Library(*a), library.Library(*b))

    @data(
        (
            (("test-lib-2", "3.3"), ("test-lib-1", "3.3")),
            (("test-lib-b", "3.3"), ("test-lib-a", "3.3")),
        )
    )
    def library_greater(self, a, b):
        self.assertGreater(library.Library(*a), library.Library(*b))

    @unittest.skipIf(PY33, "requires ST4 with py38")
    def test_library_not_equal_33_38(self):
        self.assertNotEqual(library.Library("test-lib", "3.3"), library.Library("test-lib", "3.8"))

    @unittest.skipIf(PY33, "requires ST4 with py38")
    def test_library_lesser_33_38(self):
        self.assertLess(library.Library("test-lib", "3.3"), library.Library("test-lib", "3.8"))

    @unittest.skipIf(PY33, "requires ST4 with py38")
    def test_library_greater_38_33(self):
        self.assertGreater(library.Library("test-lib", "3.8"), library.Library("test-lib", "3.3"))
