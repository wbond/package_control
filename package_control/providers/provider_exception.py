class ProviderException(Exception):
    """If a provider could not return information"""

    def __str__(self):
        return self.args[0]
