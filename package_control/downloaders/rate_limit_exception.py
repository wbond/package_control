try:
    # Python 3
    from http.client import HTTPException
    from urllib.error import URLError
except (ImportError):
    # Python 2
    from httplib import HTTPException
    from urllib2 import URLError


class RateLimitException(HTTPException, URLError):
    """
    An exception for when the rate limit of an API has been exceeded.
    """

    def __init__(self, host, limit):
        HTTPException.__init__(self)
        self.host = host
        self.limit = limit

    def __str__(self):
        return ('Rate limit of %s exceeded for %s' % (self.limit, self.host))
