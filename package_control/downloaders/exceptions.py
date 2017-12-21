class BinaryNotFoundError(Exception):

    """Necessary executable is not found in the PATH on the system."""

    pass


class HttpError(Exception):

    """
    If a downloader was able to download a URL, but the result was not a 200 or 304
    """

    def __init__(self, message, code):
        self.code = code
        super(HttpError, self).__init__(message)


class NonCleanExitError(Exception):

    """
    When an subprocess does not exit cleanly

    :param returncode:
        The command line integer return code of the subprocess
    """

    def __init__(self, returncode):
        self.returncode = returncode
        super(NonCleanExitError, self).__init__()

    def __str__(self):
        return str(self.returncode)


class NonHttpError(Exception):

    """
    A downloader had a non-clean exit, but not due to an HTTP error.
    """

    pass


class DownloaderException(Exception):

    """
    Downloader can not download a URL.
    """

    pass


class RateLimitException(DownloaderException):

    """
    An exception for when the rate limit of an API has been exceeded.
    """

    def __init__(self, domain, limit):
        self.domain = domain
        self.limit = limit
        message = 'Rate limit of %s exceeded for %s' % (limit, domain)
        super(RateLimitException, self).__init__(message)


class WinDownloaderException(DownloaderException):

    """
    If the WinInetDownloader ran into a windows-specific error. The means we
    should retry with the UrllibDownloader.
    """

    pass
