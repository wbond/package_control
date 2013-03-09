import re

from ..clients.github_client import GitHubClient


class GitHubUserProvider():
    """
    Allows using a GitHub user/organization as the source for multiple packages,
    or in Package Control terminology, a "repository".

    :param repo:
        The public web URL to the GitHub user/org. Should be in the format
        `https://github.com/user`.

    :param package_manager:
        An instance of :class:`PackageManager` used to access the API
    """

    def __init__(self, repo, package_manager):
        self.repo = repo
        self.package_manager = package_manager

    def match_url(self):
        """Indicates if this provider can handle the provided repo"""

        return re.search('^https?://github.com/[^/]+/?$', self.repo) != None

    def get_packages(self):
        """Uses the GitHub API to construct necessary info for all packages"""

        client = GitHubClient(self.package_manager)

        user_repos = client.user_info(self.repo)
        if user_repos == False:
            return False

        output = []
        for repo_info in user_repos:
            download = client.download_info('https://github.com/' + repo_info['user_repo'])

            output.append({
                'name': repo_info['name'],
                'description': repo_info['description'],
                'url': repo_info['url'],
                'author': repo_info['author'],
                'last_modified': download.get('date'),
                'download': download
            })

        return output

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
