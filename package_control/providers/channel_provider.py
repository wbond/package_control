import json
import os
import re
from itertools import chain
from urllib.parse import urljoin

from ..console_write import console_write
from ..download_manager import http_get, update_url
from ..versions import version_sort
from .provider_exception import ProviderException
from .schema_compat import platforms_to_releases
from .schema_compat import SchemaVersion


class InvalidChannelFileException(ProviderException):

    def __init__(self, channel, reason_message):
        super().__init__(
            'Channel %s does not appear to be a valid channel file because'
            ' %s' % (channel.url, reason_message))


class ChannelProvider:
    """
    Retrieves a channel and provides an API into the information

    The current channel/repository infrastructure caches repository info into
    the channel to improve the Package Control client performance. This also
    has the side effect of lessening the load on the GitHub and BitBucket APIs
    and getting around not-infrequent HTTP 503 errors from those APIs.

    :param channel_url:
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
          `query_string_params`,
          `http_basic_auth`
    """

    __slots__ = [
        'channel_info',
        'channel_url',
        'schema_version',
        'settings',
    ]

    def __init__(self, channel_url, settings):
        self.channel_info = None
        self.channel_url = channel_url
        self.schema_version = None
        self.settings = settings

    @classmethod
    def match_url(cls, channel_url):
        """
        Indicates if this provider can handle the provided channel_url.
        """

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
            InvalidChannelFileException: when parsing or validation file content fails
            ProviderException: when an error occurs trying to open a file
            DownloaderException: when an error occurs trying to open a URL
        """

        if self.channel_info is not None:
            return

        if re.match(r'https?://', self.channel_url, re.I):
            json_string = http_get(self.channel_url, self.settings, 'Error downloading channel.')

        # All other channels are expected to be filesystem paths
        else:
            if not os.path.exists(self.channel_url):
                raise ProviderException('Error, file %s does not exist' % self.channel_url)

            if self.settings.get('debug'):
                console_write(
                    '''
                    Loading %s as a channel
                    ''',
                    self.channel_url
                )

            # We open as binary so we get bytes like the DownloadManager
            with open(self.channel_url, 'rb') as f:
                json_string = f.read()

        try:
            channel_info = json.loads(json_string.decode('utf-8'))
        except ValueError:
            raise InvalidChannelFileException(self, 'parsing JSON failed.')

        try:
            schema_version = SchemaVersion(channel_info['schema_version'])
        except KeyError:
            raise InvalidChannelFileException(self, 'the "schema_version" JSON key is missing.')
        except ValueError as e:
            raise InvalidChannelFileException(self, e)

        if 'repositories' not in channel_info:
            raise InvalidChannelFileException(self, 'the "repositories" JSON key is missing.')

        self.channel_info = self._migrate_channel_info(channel_info, schema_version)
        self.schema_version = schema_version

    def get_name_map(self):
        """
        :raises:
            ProviderException: when an error occurs with the channel contents
            DownloaderException: when an error occurs trying to open a URL

        :return:
            A dict of the mapping for URL slug -> package name
        """

        self.fetch()

        if self.schema_version.major >= 2:
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

        if self.schema_version.major >= 2:
            output = {}
            for package in chain(*self.channel_info.get('packages_cache', {}).values()):
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

        return self.channel_info['repositories']

    def get_sources(self):
        """
        Return a list of current URLs that are directly referenced by the
        channel

        :return:
            A list of URLs and/or file paths
        """

        return self.get_repositories()

    def get_packages(self, repo_url):
        """
        Provides access to the repository info that is cached in a channel

        :param repo_url:
            The URL of the repository to get the cached info of

        :raises:
            ProviderException: when an error occurs with the channel contents
            DownloaderException: when an error occurs trying to open a URL

        :return:
            A generator of
            (
                'Package Name',
                {
                    'name': name,
                    'description': description,
                    'author': author,
                    'homepage': homepage,
                    'previous_names': [old_name, ...],
                    'labels': [label, ...],
                    'readme': url,
                    'issues': url,
                    'donate': url,
                    'buy': url,
                    'last_modified': last modified date,
                    'releases': [
                        {
                            'sublime_text': compatible version,
                            'platforms': [platform name, ...],
                            'url': url,
                            'date': date,
                            'version': version,
                            'libraries': [library name, ...]
                        }, ...
                    ]
                }
            )
            tuples
        """

        self.fetch()

        for package in self.channel_info.get('packages_cache', {}).get(repo_url, []):
            yield (package['name'], package)

    def get_libraries(self, repo_url):
        """
        Provides access to the library info that is cached in a channel

        :param repo_url:
            The URL of the repository to get the cached info of

        :raises:
            ProviderException: when an error occurs with the channel contents
            DownloaderException: when an error occurs trying to open a URL

        :return:
            A generator of
            (
                'Library Name',
                {
                    'name': name,
                    'description': description,
                    'author': author,
                    'issues': URL,
                    'releases': [
                        {
                            'sublime_text': compatible version,
                            'platforms': [platform name, ...],
                            'python_versions': ['3.3', '3.8'],
                            'url': url,
                            'version': version,
                            'sha256': hex hash
                        }, ...
                    ]
                }
            )
            tuples
        """

        self.fetch()

        for library in self.channel_info.get('libraries_cache', {}).get(repo_url, []):
            yield (library['name'], library)

    def _migrate_channel_info(self, channel_info, schema_version):
        """
        Transform input channel_info to scheme version 4.0.0

        :param channel_info:
            The input channel information of any scheme version

        :param schema_version:
            The schema version of the input channel information

        :returns:
            channel_info object of scheme version 4.0.0
        """

        channel_info['repositories'] = self._migrate_repositories(channel_info, schema_version)
        channel_info['packages_cache'] = self._migrate_packages_cache(channel_info, schema_version)
        channel_info['libraries_cache'] = self._migrate_libraries_cache(channel_info, schema_version)
        return channel_info

    def _migrate_repositories(self, channel_info, schema_version):

        debug = self.settings.get('debug')

        # Determine a relative root so repositories can be defined
        # relative to the location of the channel file.
        scheme_match = re.match(r'(https?:)//', self.channel_url, re.I)
        if scheme_match is None:
            relative_base = os.path.dirname(self.channel_url)
            is_http = False
        else:
            relative_base = ''
            is_http = True

        output = []
        for repository in channel_info['repositories']:
            if repository.startswith('//'):
                if scheme_match is not None:
                    repository = scheme_match.group(1) + repository
                else:
                    repository = 'https:' + repository
            elif repository.startswith('/'):
                # We don't allow absolute repositories
                continue
            elif repository.startswith('./') or repository.startswith('../'):
                if is_http:
                    repository = urljoin(self.channel_url, repository)
                else:
                    repository = os.path.join(relative_base, repository)
                    repository = os.path.normpath(repository)
            output.append(update_url(repository, debug))

        return output

    def _migrate_packages_cache(self, channel_info, schema_version):
        """
        Transform input packages cache to scheme version 4.0.0

        :param channel_info:
            The input channel information of any scheme version

        :param schema_version:
            The schema version of the input channel information

        :returns:
            packages_cache object of scheme version 4.0.0
        """

        debug = self.settings.get('debug')

        if schema_version.major < 2:
            # The 2.0 channel schema renamed the key cached package info was
            # stored under in order to be more clear to new users.
            channel_info['packages_cache'] = channel_info.pop('packages', {})

        package_cache = channel_info.get('packages_cache', {})

        defaults = {
            'buy': None,
            'issues': None,
            'labels': [],
            'previous_names': [],
            'readme': None,
            'donate': None
        }

        for package in chain(*package_cache.values()):

            for field in defaults:
                if field not in package:
                    package[field] = defaults[field]

            # In schema version 2.0, we store a list of dicts containing info
            # about all available releases. These include "version" and
            # "platforms" keys that are used to pick the download for the
            # current machine.
            if schema_version.major < 2:
                package['releases'] = version_sort(
                    platforms_to_releases(package, debug), 'platforms', reverse=True)
                del package['platforms']

            else:
                releases = version_sort(package.get('releases', []), 'platforms', reverse=True)
                package['releases'] = releases
                package['last_modified'] = releases[0]['date'] if releases else None

            # The 4.0.0 channel schema renamed the `dependencies` key to `libraries`.
            if schema_version.major < 4:
                for release in package['releases']:
                    if 'dependencies' in release:
                        release['libraries'] = release.pop('dependencies')

        # Fix any out-dated repository URLs in packages cache
        return {update_url(name, debug): info for name, info in package_cache.items()}

    def _migrate_libraries_cache(self, channel_info, schema_version):
        """
        Transform input libraries cache to scheme version 4.0.0

        :param channel_info:
            The input channel information of any scheme version

        :param schema_version:
            The schema version of the input channel information

        :returns:
            libraries_cache object of scheme version 4.0.0
        """

        debug = self.settings.get('debug')

        if schema_version.major < 4:
            # The 4.0.0 channel schema renamed the key cached package info was
            # stored under in order to be more clear to new users.
            libraries_cache = channel_info.pop('dependencies_cache', {})

            # The 4.0.0 channel scheme drops 'load_order' from each library
            # and adds a required 'python_versions' list to each release.
            for library in chain(*libraries_cache.values()):
                del library['load_order']
                for release in library['releases']:
                    release['python_versions'] = ['3.3']
        else:
            libraries_cache = channel_info.get('libraries_cache', {})

        for library in chain(*libraries_cache.values()):
            library['releases'] = version_sort(library['releases'], 'platforms', reverse=True)

        # Fix any out-dated repository URLs in libraries cache
        return {update_url(name, debug): info for name, info in libraries_cache.items()}
