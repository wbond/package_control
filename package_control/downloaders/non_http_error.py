class NonHttpError(Exception):

    """If a downloader had a non-clean exit, but it was not due to an HTTP error"""

    def __unicode__(self):
        return self.args[0]

    def __str__(self):
        return self.__unicode__()

    def __bytes__(self):
        return self.__unicode__().encode('utf-8')
