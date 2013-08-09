import json
import re
import os
from itertools import chain

try:
    # Python 3
    from urllib.parse import urlparse
except (ImportError):
    # Python 2
    from urlparse import urlparse

from ..console_write import console_write
from .release_selector import ReleaseSelector
from .provider_exception import ProviderException
from ..downloaders.downloader_exception import DownloaderException
from ..clients.client_exception import ClientException
from ..clients.github_client import GitHubClient
from ..clients.bitbucket_client import BitBucketClient
from ..download_manager import downloader


class RepositoryProvider(ReleaseSelector):
    """
    Generic repository downloader that fetches package info

    With the current channel/repository architecture where the channel file
    caches info from all includes repositories, these package providers just
    serve the purpose of downloading packages not in the default channel.

    The structure of the JSON a repository should contain is located in
    example-packages.json.

    :param repo:
        The URL of the package repository

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
          `install_prereleases`
    """

    def __init__(self, repo, settings):
        self.cache = {}
        self.repo_info = None
        self.schema_version = 0.0
        self.repo = repo
        self.settings = settings
        self.unavailable_packages = []
        self.failed_sources = {}
        self.broken_packages = {}

    @classmethod
    def match_url(cls, repo):
        """Indicates if this provider can handle the provided repo"""

        return True

    def prefetch(self):
        """
        Go out and perform HTTP operations, caching the result

        :raises:
            DownloaderException: when there is an issue download package info
            ClientException: when there is an issue parsing package info
        """

        [name for name, info in self.get_packages()]

    def get_failed_sources(self):
        """
        List of any URLs that could not be accessed while accessing this repository

        :return:
            A generator of ("https://example.com", Exception()) tuples
        """

        return self.failed_sources.items()

    def get_broken_packages(self):
        """
        List of package names for packages that are missing information

        :return:
            A generator of ("Package Name", Exception()) tuples
        """

        return self.broken_packages.items()

    def fetch(self):
        """
        Retrieves and loads the JSON for other methods to use

        :raises:
            ProviderException: when an error occurs trying to open a file
            DownloaderException: when an error occurs trying to open a URL
        """

        if self.repo_info != None:
            return

        self.repo_info = self.fetch_location(self.repo)

        if 'includes' not in self.repo_info:
            return

        # Allow repositories to include other repositories
        if re.match('https?://', self.repo, re.I):
            url_pieces = urlparse(self.repo)
            domain = url_pieces.scheme + '://' + url_pieces.netloc
            path = '/' if url_pieces.path == '' else url_pieces.path
            if path[-1] != '/':
                path = os.path.dirname(path)
            relative_base = domain + path
        else:
            relative_base = os.path.dirname(self.repo) + '/'

        includes = self.repo_info.get('includes', [])
        del self.repo_info['includes']
        for include in includes:
            if re.match('^\./|\.\./', include):
                include = os.path.normpath(relative_base + include)
            include_info = self.fetch_location(include)
            included_packages = include_info.get('packages', [])
            self.repo_info['packages'].extend(included_packages)

    def fetch_location(self, location):
        """
        Fetches the contents of a URL of file path

        :param location:
            The URL or file path

        :raises:
            ProviderException: when an error occurs trying to open a file
            DownloaderException: when an error occurs trying to open a URL

        :return:
            A dict of the parsed JSON
        """

        if re.match('https?://', self.repo, re.I):
            with downloader(location, self.settings) as manager:
                json_string = manager.fetch(location, 'Error downloading repository.')

        # Anything that is not a URL is expected to be a filesystem path
        else:
            if not os.path.exists(location):
                raise ProviderException(u'Error, file %s does not exist' % location)

            if self.settings.get('debug'):
                console_write(u'Loading %s as a repository' % location, True)

            # We open as binary so we get bytes like the DownloadManager
            with open(location, 'rb') as f:
                json_string = f.read()

        try:
            return json.loads(json_string.decode('utf-8'))
        except (ValueError):
            raise ProviderException(u'Error parsing JSON from repository %s.' % location)

    def get_packages(self, invalid_sources=None):
        """
        Provides access to the packages in this repository

        :param invalid_sources:
            A list of URLs that are permissible to fetch data from

        :raises:
            ProviderException: when an error occurs trying to open a file
            DownloaderException: when there is an issue download package info
            ClientException: when there is an issue parsing package info

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
                    'download': {
                        'url': url,
                        'date': date,
                        'version': version
                    },
                    'previous_names': [old_name, ...],
                    'labels': [label, ...],
                    'sources': [url, ...],
                    'readme': url,
                    'issues': url,
                    'donate': url,
                    'buy': url
                }
            )
            tuples
        """

        if 'get_packages' in self.cache:
            for key, value in self.cache['get_packages'].items():
                yield (key, value)
            return

        if invalid_sources != None and self.repo in invalid_sources:
            raise StopIteration()

        self.fetch()

        def fail(message):
            exception = ProviderException(message)
            self.failed_sources[self.repo] = exception
            self.cache['get_packages'] = {}
            return
        schema_error = u'Repository %s does not appear to be a valid repository file because ' % self.repo

        if 'schema_version' not in self.repo_info:
            error_string = u'%s the "schema_version" JSON key is missing.' % schema_error
            fail(error_string)
            return

        try:
            self.schema_version = float(self.repo_info.get('schema_version'))
        except (ValueError):
            error_string = u'%s the "schema_version" is not a valid number.' % schema_error
            fail(error_string)
            return

        if self.schema_version not in [1.0, 1.1, 1.2, 2.0]:
            error_string = u'%s the "schema_version" is not recognized. Must be one of: 1.0, 1.1, 1.2 or 2.0.' % schema_error
            fail(error_string)
            return

        if 'packages' not in self.repo_info:
            error_string = u'%s the "packages" JSON key is missing.' % schema_error
            fail(error_string)
            return

        github_client = GitHubClient(self.settings)
        bitbucket_client = BitBucketClient(self.settings)

        # Backfill the "previous_names" keys for old schemas
        previous_names = {}
        if self.schema_version < 2.0:
            renamed = self.get_renamed_packages()
            for old_name in renamed:
                new_name = renamed[old_name]
                if new_name not in previous_names:
                    previous_names[new_name] = []
                previous_names[new_name].append(old_name)

        output = {}
        for package in self.repo_info['packages']:
            info = {
                'sources': [self.repo]
            }

            for field in ['name', 'description', 'author', 'last_modified', 'previous_names',
                    'labels', 'homepage', 'readme', 'issues', 'donate', 'buy']:
                if package.get(field):
                    info[field] = package.get(field)

            # Schema version 2.0 allows for grabbing details about a pacakge, or its
            # download from "details" urls. See the GitHubClient and BitBucketClient
            # classes for valid URLs.
            if self.schema_version >= 2.0:
                details = package.get('details')
                releases = package.get('releases')

                # Try to grab package-level details from GitHub or BitBucket
                if details:
                    if invalid_sources != None and details in invalid_sources:
                        continue

                    info['sources'].append(details)

                    try:
                        github_repo_info = github_client.repo_info(details)
                        bitbucket_repo_info = bitbucket_client.repo_info(details)

                        # When grabbing details, prefer explicit field values over the values
                        # from the GitHub or BitBucket API
                        if github_repo_info:
                            info = dict(chain(github_repo_info.items(), info.items()))
                        elif bitbucket_repo_info:
                            info = dict(chain(bitbucket_repo_info.items(), info.items()))
                        else:
                            raise ProviderException(u'Invalid "details" value "%s" for one of the packages in the repository %s.' % (details, self.repo))

                    except (DownloaderException, ClientException, ProviderException) as e:
                        if 'name' in info:
                            self.broken_packages[info['name']] = e
                        self.failed_sources[details] = e
                        continue

                # If no releases info was specified, also grab the download info from GH or BB
                if not releases and details:
                    releases = [{'details': details}]

                # This allows developers to specify a GH or BB location to get releases from,
                # especially tags URLs (https://github.com/user/repo/tags or
                # https://bitbucket.org/user/repo#tags)
                info['releases'] = []
                for release in releases:
                    download_details = None
                    download_info = {}

                    # Make sure that explicit fields are copied over
                    for field in ['platforms', 'sublime_text', 'version', 'url', 'date']:
                        if field in release:
                            download_info[field] = release[field]

                    if 'details' in release:
                        download_details = release['details']

                        try:
                            github_download = github_client.download_info(download_details)
                            bitbucket_download = bitbucket_client.download_info(download_details)

                            # Overlay the explicit field values over values fetched from the APIs
                            if github_download:
                                download_info = dict(chain(github_download.items(), download_info.items()))
                            # No matching tags
                            elif github_download == False:
                                download_info = {}
                            elif bitbucket_download:
                                download_info = dict(chain(bitbucket_download.items(), download_info.items()))
                            # No matching tags
                            elif bitbucket_download == False:
                                download_info = {}
                            else:
                                raise ProviderException(u'Invalid "details" value "%s" under the "releases" key for the package "%s" in the repository %s.' % (download_details, info['name'], self.repo))

                        except (DownloaderException, ClientException, ProviderException) as e:
                            if 'name' in info:
                                self.broken_packages[info['name']] = e
                            self.failed_sources[download_details] = e
                            continue

                    if download_info:
                        info['releases'].append(download_info)

                info = self.select_release(info)

            # Schema version 1.0, 1.1 and 1.2 just require that all values be
            # explicitly specified in the package JSON
            else:
                info['platforms'] = package.get('platforms')
                info = self.select_platform(info)

            if not info:
                self.unavailable_packages.append(package['name'])
                continue

            if 'download' not in info and 'releases' not in info:
                self.broken_packages[info['name']] = ProviderException(u'No "releases" key for the package "%s" in the repository %s.' % (info['name'], self.repo))
                continue

            for field in ['previous_names', 'labels']:
                if field not in info:
                    info[field] = []

            for field in ['readme', 'issues', 'donate', 'buy']:
                if field not in info:
                    info[field] = None

            if 'homepage' not in info:
                info['homepage'] = self.repo

            if 'download' in info:
                # Rewrites the legacy "zipball" URLs to the new "zip" format
                info['download']['url'] = re.sub(
                    '^(https://nodeload.github.com/[^/]+/[^/]+/)zipball(/.*)$',
                    '\\1zip\\2', info['download']['url'])

                # Rewrites the legacy "nodeload" URLs to the new "codeload" subdomain
                info['download']['url'] = info['download']['url'].replace(
                    'nodeload.github.com', 'codeload.github.com')

                # Extract the date from the download
                if 'last_modified' not in info:
                    info['last_modified'] = info['download']['date']

            elif 'releases' in info and 'last_modified' not in info:
                # Extract a date from the newest download
                date = '1970-01-01 00:00:00'
                for release in info['releases']:
                    if 'date' in release and release['date'] > date:
                        date = release['date']
                info['last_modified'] = date

            if info['name'] in previous_names:
                info['previous_names'].extend(previous_names[info['name']])

            output[info['name']] = info
            yield (info['name'], info)

        self.cache['get_packages'] = output

    def get_renamed_packages(self):
        """:return: A dict of the packages that have been renamed"""

        if self.schema_version < 2.0:
            return self.repo_info.get('renamed_packages', {})

        output = {}
        for package in self.repo_info['packages']:
            if 'previous_names' not in package:
                continue

            previous_names = package['previous_names']
            if not isinstance(previous_names, list):
                previous_names = [previous_names]

            for previous_name in previous_names:
                output[previous_name] = package['name']

        return output

    def get_unavailable_packages(self):
        """
        Provides a list of packages that are unavailable for the current
        platform/architecture that Sublime Text is running on.

        This list will be empty unless get_packages() is called first.

        :return: A list of package names
        """

        return self.unavailable_packages
