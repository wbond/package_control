from .downloader_exception import DownloaderException


class RateLimitException(DownloaderException):
    """
    An exception for when the rate limit of an API has been exceeded.
    """

    def __init__(self, domain, limit):
        self.domain = domain
        self.limit = limit
        message = u'Rate limit of %s exceeded for %s' % (limit, domain)
        super(RateLimitException, self).__init__(message)
