import httplib
import urllib2


class RateLimitException(httplib.HTTPException, urllib2.URLError):
    """
    An exception for when the rate limit of an API has been exceeded.
    """

    def __init__(self, host, limit):
        httplib.HTTPException.__init__(self)
        self.host = host
        self.limit = limit

    def __str__(self):
        return ('Rate limit of %s exceeded for %s' % (self.limit, self.host))
