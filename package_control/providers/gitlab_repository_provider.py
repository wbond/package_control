import re

from ..clients.client_exception import ClientException
from ..clients.gitlab_client import GitLabClient
from ..downloaders.downloader_exception import DownloaderException
from .base_repository_provider import BaseRepositoryProvider
from .provider_exception import ProviderException


class GitLabRepositoryProvider(BaseRepositoryProvider):
    """
    Allows using a public GitLab repository as the source for a single package.
    For legacy purposes, this can also be treated as the source for a Package
    Control "repository".

    :param repo_url:
        The public web URL to the GitLab repository. Should be in the format
        `https://gitlab.com/user/package` for the master branch, or
        `https://gitlab.com/user/package/-/tree/{branch_name}` for any other
        branch.

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

    def __init__(self, repo_url, settings):
        # Clean off the trailing .git to be more forgiving
        super().__init__(re.sub(r'\.git$', '', repo_url), settings)

    @classmethod
    def match_url(cls, repo_url):
        """Indicates if this provider can handle the provided repo_url"""

        master = re.search('^https?://gitlab.com/[^/]+/[^/]+/?$', repo_url)
        branch = re.search('^https?://gitlab.com/[^/]+/[^/]+/-/tree/[^/]+/?$', repo_url)
        return master is not None or branch is not None

    def get_packages(self, invalid_sources=None):
        """
        Uses the GitLab API to construct necessary info for a package

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

        client = GitLabClient(self.settings)

        try:
            repo_info = client.repo_info(self.repo_url)

            releases = []
            for download in client.download_info(self.repo_url):
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
