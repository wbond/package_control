try:
    # Python 3
    from urllib.parse import urlparse
    str_cls = str
except (ImportError):
    # Python 2
    from urlparse import urlparse
    str_cls = unicode  # noqa

from .rate_limit_exception import RateLimitException


class LimitingDownloader(object):

    """
    A base for downloaders that checks for rate limiting headers.
    """

    def handle_rate_limit(self, headers, url):
        """
        Checks the headers of a response object to make sure we are obeying the
        rate limit

        :param headers:
            The dict-like object that contains lower-cased headers

        :param url:
            The URL that was requested

        :raises:
            RateLimitException when the rate limit has been hit
        """

        limit_remaining = headers.get('x-ratelimit-remaining', '1')
        limit = headers.get('x-ratelimit-limit', '1')

        if str_cls(limit_remaining) == '0':
            hostname = urlparse(url).hostname
            raise RateLimitException(hostname, limit)
