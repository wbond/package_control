class DownloaderException(Exception):

    """If a downloader could not download a URL"""

    def __bytes__(self):
        return self.__str__().encode('utf-8')
