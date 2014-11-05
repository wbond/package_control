from .downloader_exception import DownloaderException


class WinDownloaderException(DownloaderException):
    """
    If the WinInetDownloader ran into a windows-specific error. The means we
    should retry with the UrllibDownloader.
    """

    pass
