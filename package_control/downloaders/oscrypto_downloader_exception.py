from .downloader_exception import DownloaderException


class OscryptoDownloaderException(DownloaderException):

    """
    If the OscryptoDownloader ran into an error. Most likely a non-HTTPS
    connection or non-HTTPS proxy. The means we should retry with the
    UrllibDownloader.
    """

    pass
