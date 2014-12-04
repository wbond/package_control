import re

from ..clients.bitbucket_client import BitBucketClient
from ..downloaders.downloader_exception import DownloaderException
from ..clients.client_exception import ClientException
from .provider_exception import ProviderException


class BitBucketRepositoryProvider():
    """
    Allows using a public BitBucket repository as the source for a single package.
    For legacy purposes, this can also be treated as the source for a Package
    Control "repository".

    :param repo:
        The public web URL to the BitBucket repository. Should be in the format
        `https://bitbucket.org/user/package`.

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

    def __init__(self, repo, settings):
        self.cache = {}
        self.repo = repo
        self.settings = settings
        self.failed_sources = {}

    @classmethod
    def match_url(cls, repo):
        """Indicates if this provider can handle the provided repo"""

        return re.search('^https?://bitbucket.org/([^/]+/[^/]+)/?$', repo) != None

    def prefetch(self):
        """
        Go out and perform HTTP operations, caching the result

        :raises:
            DownloaderException: when there is an issue download package info
            ClientException: when there is an issue parsing package info
        """

        [name for name, info in self.get_packages()]

    def get_failed_sources(self):
        """
        List of any URLs that could not be accessed while accessing this repository

        :return:
            A generator of ("https://bitbucket.org/user/repo", Exception()) tuples
        """

        return self.failed_sources.items()

    def get_broken_packages(self):
        """
        For API-compatibility with RepositoryProvider
        """

        return {}.items()

    def get_broken_dependencies(self):
        """
        For API-compatibility with RepositoryProvider
        """

        return {}.items()

    def get_dependencies(self, ):
        "For API-compatibility with RepositoryProvider"

        return {}.items()

    def get_packages(self, invalid_sources=None):
        """
        Uses the BitBucket API to construct necessary info for a package

        :param invalid_sources:
            A list of URLs that should be ignored

        :raises:
            DownloaderException: when there is an issue download package info
            ClientException: when there is an issue parsing package info

        :return:
            A generator of
            (
                'Package Name',
                {
                    'name': name,
                    'description': description,
                    'author': author,
                    'homepage': homepage,
                    'last_modified': last modified date,
                    'releases': [
                        {
                            'sublime_text': '*',
                            'platforms': ['*'],
                            'url': url,
                            'date': date,
                            'version': version
                        }, ...
                    ],
                    'previous_names': [],
                    'labels': [],
                    'sources': [the repo URL],
                    'readme': url,
                    'issues': url,
                    'donate': url,
                    'buy': None
                }
            )
            tuples
        """

        if 'get_packages' in self.cache:
            for key, value in self.cache['get_packages'].items():
                yield (key, value)
            return

        client = BitBucketClient(self.settings)

        if invalid_sources != None and self.repo in invalid_sources:
            raise StopIteration()

        try:
            repo_info = client.repo_info(self.repo)

            releases = []
            for download in client.download_info(self.repo):
                download['sublime_text'] = '*'
                download['platforms'] = ['*']
                releases.append(download)

            name = repo_info['name']
            details = {
                'name': name,
                'description': repo_info['description'],
                'homepage': repo_info['homepage'],
                'author': repo_info['author'],
                'last_modified': releases[0].get('date'),
                'releases': releases,
                'previous_names': [],
                'labels': [],
                'sources': [self.repo],
                'readme': repo_info['readme'],
                'issues': repo_info['issues'],
                'donate': repo_info['donate'],
                'buy': None
            }
            self.cache['get_packages'] = {name: details}
            yield (name, details)

        except (DownloaderException, ClientException, ProviderException) as e:
            self.failed_sources[self.repo] = e
            self.cache['get_packages'] = {}
            raise StopIteration()

    def get_sources(self):
        """
        Return a list of current URLs that are directly referenced by the repo

        :return:
            A list of URLs
        """

        return [self.repo]

    def get_renamed_packages(self):
        """For API-compatibility with RepositoryProvider"""

        return {}
