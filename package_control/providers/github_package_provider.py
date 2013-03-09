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

    :param package_manager:
        An instance of :class:`PackageManager` used to access the API
    """

    def __init__(self, repo, package_manager):
        # Clean off the trailing .git to be more forgiving
        self.repo = re.sub('\.git$', '', repo)
        self.package_manager = package_manager

    def match_url(self):
        """Indicates if this provider can handle the provided repo"""

        master = re.search('^https?://github.com/[^/]+/[^/]+/?$', self.repo)
        branch = re.search('^https?://github.com/[^/]+/[^/]+/tree/[^/]+/?$',
            self.repo)
        return master != None or branch != None

    def get_package(self):
        """
        Uses the GitHub API to construct necessary info for a package

        :return:
            A list with a single dict containing the keys: "name",
            "description", "url", "author", "last_modified", "download"
        """

        client = GitHubClient(self.package_manager)

        repo_info = client.repo_info(self.repo)
        if repo_info == False:
            return False

        download = client.download_info(self.repo)
        if download == False:
            return False

        return [{
            'name': repo_info['name'],
            'description': repo_info['description'],
            'url': repo_info['url'],
            'author': repo_info['author'],
            'last_modified': download.get('date'),
            'download': download
        }]

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
