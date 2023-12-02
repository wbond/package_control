# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import os
import site
import sys


PACKAGE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


DEPS_DIR = os.path.join(PACKAGE_ROOT, 'dev', '.lint-deps')
if os.path.exists(DEPS_DIR):
    site.addsitedir(DEPS_DIR)


import flake8
if not hasattr(flake8, '__version_info__') or flake8.__version_info__ < (3,):
    from flake8.engine import get_style_guide
else:
    from flake8.api.legacy import get_style_guide


def run():
    """
    Runs flake8 lint

    :return:
        A bool - if flake8 did not find any errors
    """

    print('Python %s' % sys.version)
    print('Running flake8 %s' % flake8.__version__)

    flake8_style = get_style_guide(config_file=os.path.join(PACKAGE_ROOT, 'tox.ini'))

    paths = []
    for root, _, filenames in os.walk('package_control'):
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            paths.append(os.path.join(root, filename))
    for filename in os.listdir(PACKAGE_ROOT):
        if not filename.endswith('.py'):
            continue
        paths.append(filename)
    report = flake8_style.check_files(paths)
    success = report.total_errors == 0
    if success:
        print('OK')
    return success


if __name__ == "__main__":
    result = run()
    sys.exit(int(not result))
