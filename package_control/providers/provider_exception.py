class ProviderException(Exception):

    """If a provider could not return information"""

    def __bytes__(self):
        return self.__str__().encode('utf-8')
