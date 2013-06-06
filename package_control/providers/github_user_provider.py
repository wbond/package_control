import re

from ..clients.github_client import GitHubClient


class GitHubUserProvider():
    """
    Allows using a GitHub user/organization as the source for multiple packages,
    or in Package Control terminology, a "repository".

    :param repo:
        The public web URL to the GitHub user/org. Should be in the format
        `https://github.com/user`.

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
          `query_string_params`
          `install_prereleases`
    """

    def __init__(self, repo, settings):
        self.cache = {}
        self.repo = repo
        self.settings = settings

    @classmethod
    def match_url(cls, repo):
        """Indicates if this provider can handle the provided repo"""

        return re.search('^https?://github.com/[^/]+/?$', repo) != None

    def prefetch(self):
        """
        Go out and perform HTTP operations, caching the result
        """

        self.get_packages()

    def get_failed_sources(self):
        """
        List of any URLs that could not be accessed while accessing this repository

        :return:
            A list of strings containing URLs
        """

        if 'get_packages' in self.cache and self.cache['get_packages'] == False:
            return [self.repo]
        return []

    def get_broken_packages(self):
        """
        For API-compatibility with RepositoryProvider
        """

        return []

    def get_packages(self, valid_sources=None):
        """
        Uses the GitHub API to construct necessary info for all packages

        :param valid_sources:
            A list of URLs that are permissible to fetch data from

        :return:
            A dict in the format:
            {
                'Package Name': {
                    'name': name,
                    'description': description,
                    'author': author,
                    'homepage': homepage,
                    'last_modified': last modified date,
                    'download': {
                        'url': url,
                        'date': date,
                        'version': version
                    },
                    'previous_names': [],
                    'labels': [],
                    'sources': [the user URL],
                    'readme': url,
                    'issues': url,
                    'donate': url,
                    'buy': None
                },
                ...
            }
            False if there is an error or None if no match
        """

        if 'get_packages' in self.cache:
            return self.cache['get_packages']

        client = GitHubClient(self.settings)

        if valid_sources != None and self.repo not in valid_sources:
            self.cache['get_packages'] = None
            return None

        user_repos = client.user_info(self.repo)
        if not user_repos:
            self.cache['get_packages'] = user_repos
            return user_repos

        output = {}
        for repo_info in user_repos:
            download = client.download_info('https://github.com/' + repo_info['user_repo'])

            output[repo_info['name']] = {
                'name': repo_info['name'],
                'description': repo_info['description'],
                'homepage': repo_info['homepage'],
                'author': repo_info['author'],
                'last_modified': download.get('date'),
                'download': download,
                'previous_names': [],
                'labels': [],
                'sources': [self.repo],
                'readme': repo_info['readme'],
                'issues': repo_info['issues'],
                'donate': repo_info['donate'],
                'buy': None
            }

        self.cache['get_packages'] = output
        return output

    def get_renamed_packages(self):
        """For API-compatibility with RepositoryProvider"""

        return {}

    def get_unavailable_packages(self):
        """
        Method for compatibility with RepositoryProvider class. These providers
        are based on API calls, and thus do not support different platform
        downloads, making it impossible for there to be unavailable packages.

        :return: An empty list
        """
        return []
