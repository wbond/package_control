class ClientException(Exception):

    """If a client could not fetch information"""

    def __bytes__(self):
        return self.__str__().encode('utf-8')
