class NonHttpError(Exception):

    """If a downloader had a non-clean exit, but it was not due to an HTTP error"""

    def __bytes__(self):
        return self.__str__().encode('utf-8')
