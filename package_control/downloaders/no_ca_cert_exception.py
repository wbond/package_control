try:
    # Python 3
    from http.client import HTTPException
    from urllib.error import URLError
except (ImportError):
    # Python 2
    from httplib import HTTPException
    from urllib2 import URLError


class NoCaCertException(HTTPException, URLError):
    """
    An exception for when there is no CA cert for a domain name
    """

    def __init__(self, host):
        HTTPException.__init__(self)
        self.host = host

    def __str__(self):
        return ('No CA certs available for %s' % self.host)
