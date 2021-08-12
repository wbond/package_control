import os
import re

from .. import __version__


LAST_COMMIT_TIMESTAMP = '2014-11-28 20:54:15'
LAST_COMMIT_VERSION = re.sub(r'[ :\-]', '.', LAST_COMMIT_TIMESTAMP)

GH_USER = os.environ.get('GH_USER', 'packagecontrol-bot')
GH_PASS = os.environ.get('GH_PASS', '')

GL_USER = os.environ.get('GL_USER', 'wbond')
GL_PASS = os.environ.get('GL_PASS', '')

BB_USER = os.environ.get('BB_USER', 'wbond')
BB_PASS = os.environ.get('BB_PASS', '')

USER_AGENT = 'Package Control %s Unittests' % __version__

DEBUG = False
