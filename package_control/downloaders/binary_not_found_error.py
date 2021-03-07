class BinaryNotFoundError(Exception):

    """If a necessary executable is not found in the PATH on the system"""

    def __bytes__(self):
        return self.__str__().encode('utf-8')
