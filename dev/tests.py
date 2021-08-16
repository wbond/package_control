# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import importlib.machinery
import os
import re
import sys
import unittest


PACKAGE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

sys.path.append(PACKAGE_ROOT)

# Mock the sublime module for CLI usage
sublime = importlib.machinery.SourceFileLoader(
    "sublime",
    os.path.join(PACKAGE_ROOT, "dev/sublime.py")
).load_module()


import package_control.tests


def run(matcher=None):
    """
    Runs tests

    :param matcher:
        A unicode string containing a regular expression to use to filter test
        names by. A value of None will cause no filtering.

    :return:
        A bool - if tests did not find any errors
    """

    print('Python %s' % sys.version)
    print('Running tests')

    loader = unittest.TestLoader()
    test_list = []
    for test_class in package_control.tests.TEST_CLASSES:
        if matcher:
            names = loader.getTestCaseNames(test_class)
            for name in names:
                if re.search(matcher, name):
                    test_list.append(test_class(name))
        else:
            test_list.append(loader.loadTestsFromTestCase(test_class))

    stream = sys.stdout
    verbosity = 1
    if matcher:
        verbosity = 2

    suite = unittest.TestSuite()
    for test in test_list:
        suite.addTest(test)
    result = unittest.TextTestRunner(stream=stream, verbosity=verbosity).run(suite)

    return len(result.errors) == 0 and len(result.failures) == 0


if __name__ == "__main__":
    if len(sys.argv) == 2:
        result = run(sys.argv[1])
    else:
        result = run()
    sys.exit(int(not result))
