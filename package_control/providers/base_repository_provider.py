class BaseRepositoryProvider:
    """
    Base repository downloader that fetches package info

    This base class acts as interface to ensure all providers expose the same
    set of methods. All providers should therefore derive from this base class.

    The structure of the JSON a repository should contain is located in
    example-packages.json.

    :param repo_url:
        The URL of the package repository

    :param settings:
        A dict containing at least the following fields:
          `cache_length`,
          `debug`,
          `timeout`,
          `user_agent`
        Optional fields:
          `http_proxy`,
          `https_proxy`,
          `proxy_username`,
          `proxy_password`,
          `query_string_params`
    """

    __slots__ = [
        'broken_libriaries',
        'broken_packages',
        'failed_sources',
        'libraries',
        'packages',
        'repo_url',
        'settings',
    ]

    def __init__(self, repo_url, settings):
        self.broken_libriaries = {}
        self.broken_packages = {}
        self.failed_sources = {}
        self.libraries = None
        self.packages = None
        self.repo_url = repo_url
        self.settings = settings

    @classmethod
    def match_url(cls, repo_url):
        """
        Indicates if this provider can handle the provided repo_url
        """

        return True

    def prefetch(self):
        """
        Go out and perform HTTP operations, caching the result
        """

        [name for name, info in self.get_packages()]

    def fetch(self):
        """
        Retrieves and loads the JSON for other methods to use

        :raises:
            NotImplementedError: when called
        """

        raise NotImplementedError()

    def get_broken_libraries(self):
        """
        List of library names for libraries that are missing information

        :return:
            A generator of ("Library Name", Exception()) tuples
        """

        return self.broken_libriaries.items()

    def get_broken_packages(self):
        """
        List of package names for packages that are missing information

        :return:
            A generator of ("Package Name", Exception()) tuples
        """

        return self.broken_packages.items()

    def get_failed_sources(self):
        """
        List of any URLs that could not be accessed while accessing this repository

        :return:
            A generator of ("https://example.com", Exception()) tuples
        """

        return self.failed_sources.items()

    def get_libraries(self, invalid_sources=None):
        """
        For API-compatibility with RepositoryProvider
        """

        return {}.items()

    def get_packages(self, invalid_sources=None):
        """
        For API-compatibility with RepositoryProvider
        """

        return {}.items()

    def get_sources(self):
        """
        Return a list of current URLs that are directly referenced by the repo

        :return:
            A list of URLs
        """

        return [self.repo_url]

    def get_renamed_packages(self):
        """For API-compatibility with RepositoryProvider"""

        return {}
