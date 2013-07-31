class DownloaderException(Exception):
    """If a downloader could not download a URL"""

    def __str__(self):
        return self.args[0]
