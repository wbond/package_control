from .downloader_exception import DownloaderException


class RateLimitException(DownloaderException):

    """
    An exception for when the rate limit of an API has been exceeded.
    """

    def __init__(self, domain, limit):
        self.domain = domain
        self.limit = limit

    def __str__(self):
        return 'Hit rate limit of %s for %s.' % (self.limit, self.domain)


class RateLimitSkipException(DownloaderException):

    """
    An exception for when skipping requests due to rate limit of an API has been exceeded.
    """

    def __init__(self, domain):
        self.domain = domain

    def __str__(self):
        return 'Skipping %s due to rate limit.' % self.domain
