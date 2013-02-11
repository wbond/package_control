import json
import re

from ..console_write import console_write
from .platform_comparator import PlatformComparator


class PackageProvider(PlatformComparator):
    """
    Generic repository downloader that fetches package info

    With the current channel/repository architecture where the channel file
    caches info from all includes repositories, these package providers just
    serve the purpose of downloading packages not in the default channel.

    The structure of the JSON a repository should contain is located in
    example-packages.json.

    :param repo:
        The URL of the package repository

    :param package_manager:
        An instance of :class:`PackageManager` used to download the file
    """

    def __init__(self, repo, package_manager):
        self.repo_info = None
        self.repo = repo
        self.package_manager = package_manager
        self.unavailable_packages = []

    def match_url(self):
        """Indicates if this provider can handle the provided repo"""

        return True

    def fetch_repo(self):
        """Retrieves and loads the JSON for other methods to use"""

        if self.repo_info != None:
            return

        repository_json = self.package_manager.download_url(self.repo,
            'Error downloading repository.')
        if repository_json == False:
            self.repo_info = False
            return

        try:
            self.repo_info = json.loads(repository_json.decode('utf-8'))
        except (ValueError):
            console_write(u'Error parsing JSON from repository %s.' % self.repo, True)
            self.repo_info = False

    def get_packages(self):
        """
        Provides access to the repository info that is cached in a channel

        :return:
            A dict in the format:
            {
                'Package Name': {
                    # Package details - see example-packages.json for format
                },
                ...
            }
            or False if there is an error
        """

        self.fetch_repo()
        if self.repo_info == False:
            return False

        output = {}

        schema_error = u'Repository %s does not appear to be a valid repository file because ' % self.repo

        if 'schema_version' not in self.repo_info:
            console_write(u'%s the "schema_version" JSON key is missing.' % schema_error, True)
            return False

        if str(self.repo_info['schema_version']) not in ['1.0', '1.1', '1.2']:
            console_write(u'%s the "schema_version" is not recognized. Must be one of: 1.0, 1.1 or 1.2.' % schema_error, True)
            return False

        if 'packages' not in self.repo_info:
            console_write(u'%s the "packages" JSON key is missing.' % schema_error, True)
            return False

        for package in self.repo_info['packages']:

            platforms = list(package['platforms'].keys())
            best_platform = self.get_best_platform(platforms)

            if not best_platform:
                self.unavailable_packages.append(package['name'])
                continue

            # Rewrites the legacy "zipball" URLs to the new "zip" format
            downloads = package['platforms'][best_platform]
            rewritten_downloads = []
            for download in downloads:
                download['url'] = re.sub(
                    '^(https://nodeload.github.com/[^/]+/[^/]+/)zipball(/.*)$',
                    '\\1zip\\2', download['url'])
                rewritten_downloads.append(download)

            info = {
                'name': package['name'],
                'description': package.get('description'),
                'url': package.get('homepage', self.repo),
                'author': package.get('author'),
                'last_modified': package.get('last_modified'),
                'downloads': rewritten_downloads
            }

            output[package['name']] = info

        return output

    def get_renamed_packages(self):
        """:return: A dict of the packages that have been renamed"""

        return self.repo_info.get('renamed_packages', {})

    def get_unavailable_packages(self):
        """
        Provides a list of packages that are unavailable for the current
        platform/architecture that Sublime Text is running on.

        This list will be empty unless get_packages() is called first.

        :return: A list of package names
        """

        return self.unavailable_packages
