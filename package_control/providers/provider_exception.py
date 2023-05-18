class ProviderException(Exception):

    """If a provider could not return information"""

    def __bytes__(self):
        return self.__str__().encode('utf-8')


class GitProviderUserInfoException(ProviderException):
    """
    Exception for signalling user information download error.

    The exception is used to indicate a given URL not being in expected form
    to be used by given provider to download user info from.
    """

    def __init__(self, provider):
        self.provider_name = provider.__class__.__name__
        self.url = provider.repo_url

    def __str__(self):
        return '%s unable to fetch user information from "%s".' % (self.provider_name, self.url)


class GitProviderRepoInfoException(ProviderException):
    """
    Exception for signalling repository information download error.

    The exception is used to indicate a given URL not being in expected form
    to be used by given provider to download repo info from.
    """

    def __init__(self, provider):
        self.provider_name = provider.__class__.__name__
        self.url = provider.repo_url

    def __str__(self):
        return '%s unable to fetch repo information from "%s".' % (self.provider_name, self.url)


class GitProviderDownloadInfoException(ProviderException):
    """
    Exception for signalling download information download error.

    The exception is used to indicate a given URL not being in expected form
    to be used by given provider to download release information from.
    """

    def __init__(self, provider, url=None):
        self.provider_name = provider.__class__.__name__
        self.url = url or provider.repo_url

    def __str__(self):
        return '%s unable to fetch download information from "%s".' % (self.provider_name, self.url)
