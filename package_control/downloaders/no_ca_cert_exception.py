from .downloader_exception import DownloaderException


class NoCaCertException(DownloaderException):
    """
    An exception for when there is no CA cert for a domain name
    """

    def __init__(self, message, domain):
        self.domain = domain
        super(NoCaCertException, self).__init__(message)
