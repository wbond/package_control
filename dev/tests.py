# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import os
import sys
import unittest


PACKAGE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

sys.path.append(PACKAGE_ROOT)


def run():
    """
    Runs tests

    :return:
        A bool - if tests did not find any errors
    """

    print('Python %s' % sys.version)
    print('Running tests')

    suite = unittest.TestLoader().discover(
        pattern="test_*.py",
        start_dir="package_control/tests",
        top_level_dir=PACKAGE_ROOT
    )

    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)

    return len(result.errors) == 0 and len(result.failures) == 0


if __name__ == "__main__":
    result = run()
    sys.exit(int(not result))
