import re

from .. import __version__

LAST_COMMIT_TIMESTAMP = '2014-11-28 20:54:15'
LAST_COMMIT_VERSION = re.sub(r'[ :\-]', '.', LAST_COMMIT_TIMESTAMP)

CLIENT_ID = ''
CLIENT_SECRET = ''

USER_AGENT = 'Package Control %s' % __version__
