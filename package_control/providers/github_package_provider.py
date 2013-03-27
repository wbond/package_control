import re

from ..clients.github_client import GitHubClient


class GitHubPackageProvider():
    """
    Allows using a public GitHub repository as the source for a single package.
    For legacy purposes, this can also be treated as the source for a Package
    Control "repository".

    :param repo:
        The public web URL to the GitHub repository. Should be in the format
        `https://github.com/user/package` for the master branch, or
        `https://github.com/user/package/tree/{branch_name}` for any other
        branch.

    :param settings:
        A dict containing at least the following fields:
          `cache_length`,
          `debug`,
          `timeout`,
          `user_agent`,
          `http_proxy`,
          `https_proxy`,
          `proxy_username`,
          `proxy_password`
        Optional fields:
          `query_string_params`
    """

    def __init__(self, repo, settings):
        # Clean off the trailing .git to be more forgiving
        self.repo = re.sub('\.git$', '', repo)
        self.settings = settings

    def match_url(self):
        """Indicates if this provider can handle the provided repo"""

        master = re.search('^https?://github.com/[^/]+/[^/]+/?$', self.repo)
        branch = re.search('^https?://github.com/[^/]+/[^/]+/tree/[^/]+/?$',
            self.repo)
        return master != None or branch != None

    def get_packages(self):
        """
        Uses the GitHub API to construct necessary info for a package

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
                    'labels': []
                }
            }
            or False if there is an error
        """

        client = GitHubClient(self.settings)

        repo_info = client.repo_info(self.repo)
        if repo_info == False:
            return False

        download = client.download_info(self.repo)
        if download == False:
            return False

        return {repo_info['name']: {
            'name': repo_info['name'],
            'description': repo_info['description'],
            'homepage': repo_info['homepage'],
            'author': repo_info['author'],
            'last_modified': download.get('date'),
            'download': download,
            'previous_names': []
        }}

    def get_renamed_packages(self):
        """For API-compatibility with :class:`PackageProvider`"""

        return {}

    def get_unavailable_packages(self):
        """
        Method for compatibility with PackageProvider class. These providers
        are based on API calls, and thus do not support different platform
        downloads, making it impossible for there to be unavailable packages.

        :return: An empty list
        """
        return []
