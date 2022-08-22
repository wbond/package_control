import re

from ..clients.client_exception import ClientException
from ..clients.gitlab_client import GitLabClient
from ..downloaders.downloader_exception import DownloaderException
from .base_repository_provider import BaseRepositoryProvider
from .provider_exception import ProviderException


class GitLabUserProvider(BaseRepositoryProvider):
    """
    Allows using a GitLab user/organization as the source for multiple packages,
    or in Package Control terminology, a 'repository'.

    :param repo_url:
        The public web URL to the GitHub user/org. Should be in the format
        `https://gitlab.com/user`.

    :param settings:
        A dict containing at least the following fields:
          `cache_length`,
          `debug`,
          `timeout`,
          `user_agent`,
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
                https://gitlab.com/{user}
                https://gitlab.com/{user}/

        :return:
            True if repo_url matches an supported scheme.
        """
        return re.match(r'^https?://gitlab.com/[^/]+/?$', repo_url) is not None

    def get_packages(self, invalid_sources=None):
        """
        Uses the lab API to construct necessary info for all packages

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
                    'sources': [the user URL],
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

        client = GitLabClient(self.settings)

        try:
            user_repos = client.user_info(self.repo_url)
        except (DownloaderException, ClientException) as e:
            self.failed_sources[self.repo_url] = e
            self.cache['get_packages'] = {}
            return

        output = {}
        for repo_info in user_repos:
            author = repo_info['author']
            name = repo_info['name']
            repo_url = client.make_repo_url(author, name)

            try:
                releases = []
                for download in client.download_info_from_branch(repo_url):
                    download['sublime_text'] = '*'
                    download['platforms'] = ['*']
                    releases.append(download)

                details = {
                    'name': name,
                    'description': repo_info['description'],
                    'homepage': repo_info['homepage'],
                    'author': author,
                    'last_modified': releases[0].get('date'),
                    'releases': releases,
                    'previous_names': [],
                    'labels': [],
                    'sources': [self.repo_url],
                    'readme': repo_info['readme'],
                    'issues': repo_info['issues'],
                    'donate': repo_info['donate'],
                    'buy': None,
                }
                output[name] = details
                yield (name, details)

            except (DownloaderException, ClientException, ProviderException) as e:
                self.failed_sources[repo_url] = e

        self.cache['get_packages'] = output
