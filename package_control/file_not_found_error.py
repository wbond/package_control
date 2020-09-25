class FileNotFoundError(Exception):

    """If a file is not found"""

    def __unicode__(self):
        return self.args[0]

    def __str__(self):
        return self.__unicode__()

    def __bytes__(self):
        return self.__unicode__().encode('utf-8')
