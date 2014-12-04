import json
import os
import re

try:
    # Python 3
    from urllib.parse import urljoin
except (ImportError):
    # Python 2
    from urlparse import urljoin

from ..console_write import console_write
from .provider_exception import ProviderException
from .schema_compat import platforms_to_releases
from ..downloaders.downloader_exception import DownloaderException
from ..clients.client_exception import ClientException
from ..download_manager import downloader, update_url
from ..versions import version_sort


class ChannelProvider():
    """
    Retrieves a channel and provides an API into the information

    The current channel/repository infrastructure caches repository info into
    the channel to improve the Package Control client performance. This also
    has the side effect of lessening the load on the GitHub and BitBucket APIs
    and getting around not-infrequent HTTP 503 errors from those APIs.

    :param channel:
        The URL of the channel

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

    def __init__(self, channel, settings):
        self.channel_info = None
        self.schema_version = '0.0'
        self.schema_major_version = 0
        self.channel = channel
        self.settings = settings

    @classmethod
    def match_url(cls, channel):
        """Indicates if this provider can handle the provided channel"""

        return True

    def prefetch(self):
        """
        Go out and perform HTTP operations, caching the result

        :raises:
            ProviderException: when an error occurs trying to open a file
            DownloaderException: when an error occurs trying to open a URL
        """

        self.fetch()

    def fetch(self):
        """
        Retrieves and loads the JSON for other methods to use

        :raises:
            ProviderException: when an error occurs with the channel contents
            DownloaderException: when an error occurs trying to open a URL
        """

        if self.channel_info != None:
            return

        if re.match('https?://', self.channel, re.I):
            with downloader(self.channel, self.settings) as manager:
                channel_json = manager.fetch(self.channel,
                    'Error downloading channel.')

        # All other channels are expected to be filesystem paths
        else:
            if not os.path.exists(self.channel):
                raise ProviderException(u'Error, file %s does not exist' % self.channel)

            if self.settings.get('debug'):
                console_write(u'Loading %s as a channel' % self.channel, True)

            # We open as binary so we get bytes like the DownloadManager
            with open(self.channel, 'rb') as f:
                channel_json = f.read()

        try:
            channel_info = json.loads(channel_json.decode('utf-8'))
        except (ValueError):
            raise ProviderException(u'Error parsing JSON from channel %s.' % self.channel)

        schema_error = u'Channel %s does not appear to be a valid channel file because ' % self.channel

        if 'schema_version' not in channel_info:
            raise ProviderException(u'%s the "schema_version" JSON key is missing.' % schema_error)

        try:
            self.schema_version = channel_info.get('schema_version')
            if isinstance(self.schema_version, int):
                self.schema_version = float(self.schema_version)
            if isinstance(self.schema_version, float):
                self.schema_version = str(self.schema_version)
        except (ValueError):
            raise ProviderException(u'%s the "schema_version" is not a valid number.' % schema_error)

        if self.schema_version not in ['1.0', '1.1', '1.2', '2.0', '3.0.0']:
            raise ProviderException(u'%s the "schema_version" is not recognized. Must be one of: 1.0, 1.1, 1.2, 2.0 or 3.0.0.' % schema_error)

        version_parts = self.schema_version.split('.')
        self.schema_major_version = int(version_parts[0])

        # Fix any out-dated repository URLs in the package cache
        debug =  self.settings.get('debug')
        packages_key = 'packages_cache' if self.schema_major_version >= 2 else 'packages'
        if packages_key in channel_info:
            original_cache = channel_info[packages_key]
            new_cache = {}
            for repo in original_cache:
                new_cache[update_url(repo, debug)] = original_cache[repo]
            channel_info[packages_key] = new_cache

        self.channel_info = channel_info

    def get_name_map(self):
        """
        :raises:
            ProviderException: when an error occurs with the channel contents
            DownloaderException: when an error occurs trying to open a URL

        :return:
            A dict of the mapping for URL slug -> package name
        """

        self.fetch()

        if self.schema_major_version >= 2:
            return {}

        return self.channel_info.get('package_name_map', {})

    def get_renamed_packages(self):
        """
        :raises:
            ProviderException: when an error occurs with the channel contents
            DownloaderException: when an error occurs trying to open a URL

        :return:
            A dict of the packages that have been renamed
        """

        self.fetch()

        if self.schema_major_version >= 2:
            output = {}
            for repo in self.channel_info['packages_cache']:
                for package in self.channel_info['packages_cache'][repo]:
                    previous_names = package.get('previous_names', [])
                    if not isinstance(previous_names, list):
                        previous_names = [previous_names]
                    for previous_name in previous_names:
                        output[previous_name] = package['name']
            return output

        return self.channel_info.get('renamed_packages', {})

    def get_repositories(self):
        """
        :raises:
            ProviderException: when an error occurs with the channel contents
            DownloaderException: when an error occurs trying to open a URL

        :return:
            A list of the repository URLs
        """

        self.fetch()

        if 'repositories' not in self.channel_info:
            raise ProviderException(u'Channel %s does not appear to be a valid channel file because the "repositories" JSON key is missing.' % self.channel)

        # Determine a relative root so repositories can be defined
        # relative to the location of the channel file.
        if re.match('https?://', self.channel, re.I) is None:
            relative_base = os.path.dirname(self.channel)
            is_http = False
        else:
            is_http = True

        debug = self.settings.get('debug')
        output = []
        repositories = self.channel_info.get('repositories', [])
        for repository in repositories:
            if re.match('^\./|\.\./', repository):
                if is_http:
                    repository = urljoin(self.channel, repository)
                else:
                    repository = os.path.join(relative_base, repository)
                    repository = os.path.normpath(repository)
            output.append(update_url(repository, debug))

        return output

    def get_sources(self):
        """
        Return a list of current URLs that are directly referenced by the
        channel

        :return:
            A list of URLs and/or file paths
        """

        return self.get_repositories()

    def get_packages(self, repo):
        """
        Provides access to the repository info that is cached in a channel

        :param repo:
            The URL of the repository to get the cached info of

        :raises:
            ProviderException: when an error occurs with the channel contents
            DownloaderException: when an error occurs trying to open a URL

        :return:
            A dict in the format:
            {
                'Package Name': {
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
                    'previous_names': [old_name, ...],
                    'labels': [label, ...],
                    'readme': url,
                    'issues': url,
                    'donate': url,
                    'buy': url
                },
                ...
            }
        """

        self.fetch()

        repo = update_url(repo, self.settings.get('debug'))

        # The 2.0 channel schema renamed the key cached package info was
        # stored under in order to be more clear to new users.
        packages_key = 'packages_cache' if self.schema_major_version >= 2 else 'packages'

        if self.channel_info.get(packages_key, False) == False:
            return {}

        if self.channel_info[packages_key].get(repo, False) == False:
            return {}

        output = {}
        for package in self.channel_info[packages_key][repo]:
            copy = package.copy()

            # In schema version 2.0, we store a list of dicts containing info
            # about all available releases. These include "version" and
            # "platforms" keys that are used to pick the download for the
            # current machine.
            if self.schema_major_version < 2:
                copy['releases'] = platforms_to_releases(copy, self.settings.get('debug'))
                del copy['platforms']
            else:
                last_modified = None
                for release in copy.get('releases', []):
                    date = release.get('date')
                    if not last_modified or (date and date > last_modified):
                        last_modified = date
                copy['last_modified'] = last_modified

            defaults = {
                'buy': None,
                'issues': None,
                'labels': [],
                'previous_names': [],
                'readme': None,
                'donate': None
            }
            for field in defaults:
                if field not in copy:
                    copy[field] = defaults[field]

            copy['releases'] = version_sort(copy['releases'], 'platforms', reverse=True)

            output[copy['name']] = copy

        return output

    def get_dependencies(self, repo):
        """
        Provides access to the dependency info that is cached in a channel

        :param repo:
            The URL of the repository to get the cached info of

        :raises:
            ProviderException: when an error occurs with the channel contents
            DownloaderException: when an error occurs trying to open a URL

        :return:
            A dict in the format:
            {
                'Dependency Name': {
                    'name': name,
                    'load_order': two digit string,
                    'description': description,
                    'author': author,
                    'issues': URL,
                    'releases': [
                        {
                            'sublime_text': '*',
                            'platforms': ['*'],
                            'url': url,
                            'date': date,
                            'version': version,
                            'sha256': hex_hash
                        }, ...
                    ]
                },
                ...
            }
        """

        self.fetch()

        repo = update_url(repo, self.settings.get('debug'))

        if self.channel_info.get('dependencies_cache', False) == False:
            return {}

        if self.channel_info['dependencies_cache'].get(repo, False) == False:
            return {}

        output = {}
        for dependency in self.channel_info['dependencies_cache'][repo]:
            dependency['releases'] = version_sort(dependency['releases'], 'platforms', reverse=True)
            output[dependency['name']] = dependency

        return output
