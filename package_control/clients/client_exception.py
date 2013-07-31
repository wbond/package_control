class ClientException(Exception):
    """If a client could not fetch information"""

    def __str__(self):
        return self.args[0]
