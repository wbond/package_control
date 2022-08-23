from ..clients.bitbucket_client import BitBucketClient
from ..clients.client_exception import ClientException
from ..downloaders.downloader_exception import DownloaderException
from .base_repository_provider import BaseRepositoryProvider
from .provider_exception import (
    GitProviderDownloadInfoException,
    GitProviderRepoInfoException,
    ProviderException,
)


class BitBucketRepositoryProvider(BaseRepositoryProvider):
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
          `query_string_params`,
          `http_basic_auth`
    """

    @classmethod
    def match_url(cls, repo_url):
        """
        Indicates if this provider can handle the provided repo_url

        :param repo_url:
            The URL to the repository, in one of the forms:
                https://bitbucket.org/{user}/{repo}.git
                https://bitbucket.org/{user}/{repo}
                https://bitbucket.org/{user}/{repo}/
                https://bitbucket.org/{user}/{repo}/src/{branch}
                https://bitbucket.org/{user}/{repo}/src/{branch}/

        :return:
            True if repo_url matches an supported scheme.
        """
        user, repo, _ = BitBucketClient.user_repo_branch(repo_url)
        return bool(user and repo)

    def get_packages(self, invalid_sources=None):
        """
        Uses the BitBucket API to construct necessary info for a package

        :param invalid_sources:
            A list of URLs that should be ignored

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

        if invalid_sources is not None and self.repo_url in invalid_sources:
            return

        client = BitBucketClient(self.settings)

        try:
            repo_info = client.repo_info(self.repo_url)
            if not repo_info:
                raise GitProviderRepoInfoException(self)

            downloads = client.download_info_from_branch(self.repo_url, repo_info['default_branch'])
            if not downloads:
                raise GitProviderDownloadInfoException(self)

            for download in downloads:
                download['sublime_text'] = '*'
                download['platforms'] = ['*']

            name = repo_info['name']
            details = {
                'name': name,
                'description': repo_info['description'],
                'homepage': repo_info['homepage'],
                'author': repo_info['author'],
                'last_modified': downloads[0].get('date'),
                'releases': downloads,
                'previous_names': [],
                'labels': [],
                'sources': [self.repo_url],
                'readme': repo_info['readme'],
                'issues': repo_info['issues'],
                'donate': repo_info['donate'],
                'buy': None
            }
            self.cache['get_packages'] = {name: details}
            yield (name, details)

        except (DownloaderException, ClientException, ProviderException) as e:
            self.failed_sources[self.repo_url] = e
            self.cache['get_packages'] = {}
