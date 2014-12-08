import json
import re
import os
from itertools import chain

try:
    # Python 3
    from urllib.parse import urljoin, urlparse
except (ImportError):
    # Python 2
    from urlparse import urljoin, urlparse

from ..console_write import console_write
from .provider_exception import ProviderException
from .schema_compat import platforms_to_releases
from ..downloaders.downloader_exception import DownloaderException
from ..clients.client_exception import ClientException
from ..clients.github_client import GitHubClient
from ..clients.bitbucket_client import BitBucketClient
from ..download_manager import downloader, update_url
from ..versions import version_sort


class RepositoryProvider():
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
    """

    def __init__(self, repo, settings):
        self.cache = {}
        self.repo_info = None
        self.schema_version = '0.0'
        self.schema_major_version = 0
        self.repo = repo
        self.settings = settings
        self.failed_sources = {}
        self.broken_packages = {}
        self.broken_dependencies = {}

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

    def get_broken_dependencies(self):
        """
        List of dependency names for dependencies that are missing information

        :return:
            A generator of ("Dependency Name", Exception()) tuples
        """

        return self.broken_dependencies.items()

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
        for key in ['packages', 'dependencies']:
            if key not in self.repo_info:
                self.repo_info[key] = []

        if 'includes' not in self.repo_info:
            return

        # Allow repositories to include other repositories
        if re.match('https?://', self.repo, re.I) is None:
            relative_base = os.path.dirname(self.repo)
            is_http = False
        else:
            is_http = True

        includes = self.repo_info.get('includes', [])
        del self.repo_info['includes']
        for include in includes:
            if re.match('^\./|\.\./', include):
                if is_http:
                    include = urljoin(self.repo, include)
                else:
                    include = os.path.join(relative_base, include)
                    include = os.path.normpath(include)
            include_info = self.fetch_location(include)
            included_packages = include_info.get('packages', [])
            self.repo_info['packages'].extend(included_packages)
            included_dependencies = include_info.get('dependencies', [])
            self.repo_info['dependencies'].extend(included_dependencies)

    def fetch_and_validate(self):
        """
        Fetch the repository and validates that it is parse-able

        :return:
            Boolean if the repo was fetched and validated
        """

        if self.repo in self.failed_sources:
            return False

        if self.repo_info is not None:
            return True

        try:
            self.fetch()
        except (DownloaderException, ProviderException) as e:
            self.failed_sources[self.repo] = e
            self.cache['get_packages'] = {}
            return False

        def fail(message):
            exception = ProviderException(message)
            self.failed_sources[self.repo] = exception
            self.cache['get_packages'] = {}
            return
        schema_error = u'Repository %s does not appear to be a valid repository file because ' % self.repo

        if 'schema_version' not in self.repo_info:
            error_string = u'%s the "schema_version" JSON key is missing.' % schema_error
            fail(error_string)
            return False

        try:
            self.schema_version = self.repo_info.get('schema_version')
            if isinstance(self.schema_version, int):
                self.schema_version = float(self.schema_version)
            if isinstance(self.schema_version, float):
                self.schema_version = str(self.schema_version)
        except (ValueError):
            error_string = u'%s the "schema_version" is not a valid number.' % schema_error
            fail(error_string)
            return False

        if self.schema_version not in ['1.0', '1.1', '1.2', '2.0', '3.0.0']:
            error_string = u'%s the "schema_version" is not recognized. Must be one of: 1.0, 1.1, 1.2, 2.0 or 3.0.0.' % schema_error
            fail(error_string)
            return False

        version_parts = self.schema_version.split('.')
        self.schema_major_version = int(version_parts[0])

        if 'packages' not in self.repo_info:
            error_string = u'%s the "packages" JSON key is missing.' % schema_error
            fail(error_string)
            return False

        if isinstance(self.repo_info['packages'], dict):
            error_string = u'%s the "packages" key is an object, not an array. This indicates it is a channel not a repository.' % schema_error
            fail(error_string)
            return False

        return True

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

    def get_dependencies(self, invalid_sources=None):
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
                'Dependency Name',
                {
                    'name': name,
                    'load_order': two digit string,
                    'description': description,
                    'author': author,
                    'issues': URL,
                    'releases': [
                        {
                            'sublime_text': compatible version,
                            'platforms': [platform name, ...],
                            'url': url,
                            'version': version,
                            'sha256': hex hash
                        }, ...
                    ],
                    'sources': [url, ...]
                }
            )
            tuples
        """

        if 'get_dependencies' in self.cache:
            for key, value in self.cache['get_dependencies'].items():
                yield (key, value)
            return

        if invalid_sources != None and self.repo in invalid_sources:
            raise StopIteration()

        if not self.fetch_and_validate():
            return

        debug = self.settings.get('debug')

        github_client = GitHubClient(self.settings)
        bitbucket_client = BitBucketClient(self.settings)

        if self.schema_major_version < 3:
            self.repo_info['dependencies'] = []

        output = {}
        for dependency in self.repo_info['dependencies']:
            info = {
                'sources': [self.repo]
            }

            for field in ['name', 'description', 'author', 'issues', 'load_order']:
                if dependency.get(field):
                    info[field] = dependency.get(field)

            if 'name' not in info:
                self.failed_sources[self.repo] = ProviderException(u'No "name" value for one of the dependencies in the repository %s.' % self.repo)
                continue

            releases = dependency.get('releases', [])

            if releases and not isinstance(releases, list):
                self.broken_dependencies[info['name']] = ProviderException(u'The "releases" value is not an array for the dependency "%s" in the repository %s.' % (info['name'], self.repo))
                continue

            for release in releases:
                if 'releases' not in info:
                    info['releases'] = []

                download_details = None
                download_info = {}

                # Make sure that explicit fields are copied over
                for field in ['platforms', 'sublime_text', 'version', 'url', 'sha256']:
                    if field in release:
                        value = release[field]
                        if field == 'url':
                            value = update_url(value, debug)
                        if field == 'platforms' and not isinstance(release['platforms'], list):
                            value = [value]
                        download_info[field] = value

                if 'platforms' not in download_info:
                    download_info['platforms'] = ['*']

                tags = release.get('tags')
                branch = release.get('branch')

                if tags or branch:
                    try:
                        base = None
                        if 'base' in release:
                            base = release['base']
                        elif details:
                            base = details

                        if not base:
                            raise ProviderException(u'Missing root-level "details" key, or release-level "base" key for one of the releases of the dependency "%s" in the repository %s.' % (info['name'], self.repo))

                        github_url = False
                        bitbucket_url = False
                        extra = None

                        if tags:
                            github_url = github_client.make_tags_url(base)
                            bitbucket_url = bitbucket_client.make_tags_url(base)
                            if tags != True:
                                extra = tags

                        if branch:
                            github_url = github_client.make_branch_url(base, branch)
                            bitbucket_url = bitbucket_client.make_branch_url(base, branch)

                        if github_url:
                            downloads = github_client.download_info(github_url, extra)
                            url = github_url
                        elif bitbucket_url:
                            downloads = bitbucket_client.download_info(bitbucket_url, extra)
                            url = bitbucket_url
                        else:
                            raise ProviderException(u'Invalid "base" value "%s" for one of the releases of the dependency "%s" in the repository %s.' % (base, info['name'], self.repo))

                        if downloads == False:
                            raise ProviderException(u'No valid semver tags found at %s for the dependency "%s" in the repository %s.' % (url, info['name'], self.repo))

                        for download in downloads:
                            del download['date']
                            new_download = download_info.copy()
                            new_download.update(download)
                            info['releases'].append(new_download)

                    except (DownloaderException, ClientException, ProviderException) as e:
                        self.broken_dependencies[info['name']] = e
                        continue

                elif download_info:
                    if 'url' in download_info:
                        is_http = urlparse(download_info['url']).scheme == 'http'
                        if is_http and 'sha256' not in download_info:
                            self.broken_dependencies[info['name']] = ProviderException(u'No "sha256" key for the non-secure "url" value in one of the releases of the dependency "%s" in the repository %s.' % (info['name'], self.repo))
                            continue

                    info['releases'].append(download_info)

            if info['name'] in self.broken_dependencies:
                continue

            # Make sure the dependency has the appropriate keys. We use a
            # function here so that we can break out of multiple loops.
            def is_missing_keys():
                for key in ['author', 'releases', 'issues', 'description', 'load_order']:
                    if key not in info:
                        self.broken_dependencies[info['name']] = ProviderException(u'No "%s" key for the dependency "%s" in the repository %s.' % (key, info['name'], self.repo))
                        return True
                for release in info.get('releases', []):
                    for key in ['version', 'url', 'sublime_text', 'platforms']:
                        if key not in release:
                            self.broken_dependencies[info['name']] = ProviderException(u'Missing "%s" key for one of the releases of the dependency "%s" in the repository %s.' % (key, info['name'], self.repo))
                            return True
                return False

            if is_missing_keys():
                continue

            info['releases'] = version_sort(info['releases'], 'platforms', reverse=True)

            output[info['name']] = info
            yield (info['name'], info)

        self.cache['get_dependencies'] = output


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
                    'releases': [
                        {
                            'sublime_text': compatible version,
                            'platforms': [platform name, ...],
                            'url': url,
                            'date': date,
                            'version': version,
                            'dependencies': [dependency name, ...]
                        }, ...
                    ]
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

        if not self.fetch_and_validate():
            return

        debug = self.settings.get('debug')

        github_client = GitHubClient(self.settings)
        bitbucket_client = BitBucketClient(self.settings)

        # Backfill the "previous_names" keys for old schemas
        previous_names = {}
        if self.schema_major_version < 2:
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

            # Schema version 2.0 allows for grabbing details about a package, or its
            # download from "details" urls. See the GitHubClient and BitBucketClient
            # classes for valid URLs.
            if self.schema_major_version >= 2:
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

            if 'name' not in info:
                self.failed_sources[self.repo] = ProviderException(u'No "name" value for one of the packages in the repository %s.' % self.repo)
                continue

            info['releases'] = []
            if self.schema_major_version == 2:
                # If no releases info was specified, also grab the download info from GH or BB
                if not releases and details:
                    releases = [{'details': details}]

            if self.schema_major_version >= 2:
                if not releases:
                    e = ProviderException(u'No "releases" value for the package "%s" in the repository %s.' % (info['name'], self.repo))
                    self.broken_packages[info['name']] = e
                    continue

                if not isinstance(releases, list):
                    e = ProviderException(u'The "releases" value is not an array or the package "%s" in the repository %s.' % (info['name'], self.repo))
                    self.broken_packages[info['name']] = e
                    continue

                # This allows developers to specify a GH or BB location to get releases from,
                # especially tags URLs (https://github.com/user/repo/tags or
                # https://bitbucket.org/user/repo#tags)
                for release in releases:
                    download_details = None
                    download_info = {}

                    # Make sure that explicit fields are copied over
                    for field in ['platforms', 'sublime_text', 'version', 'url', 'date', 'dependencies']:
                        if field in release:
                            value = release[field]
                            if field == 'url':
                                value = update_url(value, debug)
                            if field == 'platforms' and not isinstance(release['platforms'], list):
                                value = [value]
                            download_info[field] = value

                    if 'platforms' not in download_info:
                        download_info['platforms'] = ['*']

                    if self.schema_major_version == 2:
                        if 'sublime_text' not in download_info:
                            download_info['sublime_text'] = '<3000'

                        if 'details' in release:
                            download_details = release['details']

                            try:
                                github_downloads = github_client.download_info(download_details)
                                bitbucket_downloads = bitbucket_client.download_info(download_details)

                                if github_downloads == False or bitbucket_downloads == False:
                                    raise ProviderException(u'No valid semver tags found at %s for the package "%s" in the repository %s.' % (download_details, info['name'], self.repo))

                                if github_downloads:
                                    downloads = github_downloads
                                elif bitbucket_downloads:
                                    downloads = bitbucket_downloads
                                else:
                                    raise ProviderException(u'Invalid "details" value "%s" under the "releases" key for the package "%s" in the repository %s.' % (download_details, info['name'], self.repo))

                                for download in downloads:
                                    new_download = download_info.copy()
                                    new_download.update(download)
                                    info['releases'].append(new_download)

                            except (DownloaderException, ClientException, ProviderException) as e:
                                self.broken_packages[info['name']] = e

                        elif download_info:
                            info['releases'].append(download_info)

                    elif self.schema_major_version == 3:
                        tags = release.get('tags')
                        branch = release.get('branch')

                        if tags or branch:
                            try:
                                base = None
                                if 'base' in release:
                                    base = release['base']
                                elif details:
                                    base = details

                                if not base:
                                    raise ProviderException(u'Missing root-level "details" key, or release-level "base" key for one of the releases of the package "%s" in the repository %s.' % (info['name'], self.repo))

                                github_url = False
                                bitbucket_url = False
                                extra = None

                                if tags:
                                    github_url = github_client.make_tags_url(base)
                                    bitbucket_url = bitbucket_client.make_tags_url(base)
                                    if tags != True:
                                        extra = tags

                                if branch:
                                    github_url = github_client.make_branch_url(base, branch)
                                    bitbucket_url = bitbucket_client.make_branch_url(base, branch)

                                if github_url:
                                    downloads = github_client.download_info(github_url, extra)
                                    url = github_url
                                elif bitbucket_url:
                                    downloads = bitbucket_client.download_info(bitbucket_url, extra)
                                    url = bitbucket_url
                                else:
                                    raise ProviderException(u'Invalid "base" value "%s" for one of the releases of the package "%s" in the repository %s.' % (base, info['name'], self.repo))

                                if downloads == False:
                                    raise ProviderException(u'No valid semver tags found at %s for the package "%s" in the repository %s.' % (url, info['name'], self.repo))

                                for download in downloads:
                                    new_download = download_info.copy()
                                    new_download.update(download)
                                    info['releases'].append(new_download)

                            except (DownloaderException, ClientException, ProviderException) as e:
                                self.broken_packages[info['name']] = e
                                continue
                        elif download_info:
                            info['releases'].append(download_info)

            # Schema version 1.0, 1.1 and 1.2 just require that all values be
            # explicitly specified in the package JSON
            else:
                info['releases'] = platforms_to_releases(package, debug)

            info['releases'] = version_sort(info['releases'], 'platforms', reverse=True)

            if info['name'] in self.broken_packages:
                continue

            if 'author' not in info:
                self.broken_packages[info['name']] = ProviderException(u'No "author" key for the package "%s" in the repository %s.' % (info['name'], self.repo))
                continue

            if 'releases' not in info:
                self.broken_packages[info['name']] = ProviderException(u'No "releases" key for the package "%s" in the repository %s.' % (info['name'], self.repo))
                continue

            # Make sure all releases have the appropriate keys. We use a
            # function here so that we can break out of multiple loops.
            def has_broken_release():
                for release in info.get('releases', []):
                    for key in ['version', 'date', 'url', 'sublime_text', 'platforms']:
                        if key not in release:
                            self.broken_packages[info['name']] = ProviderException(u'Missing "%s" key for one of the releases of the package "%s" in the repository %s.' % (key, info['name'], self.repo))
                            return True
                return False

            if has_broken_release():
                continue

            for field in ['previous_names', 'labels']:
                if field not in info:
                    info[field] = []

            if 'readme' in info:
                info['readme'] = update_url(info['readme'], debug)

            for field in ['description', 'readme', 'issues', 'donate', 'buy']:
                if field not in info:
                    info[field] = None

            if 'homepage' not in info:
                info['homepage'] = self.repo

            if 'releases' in info and 'last_modified' not in info:
                # Extract a date from the newest release
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

    def get_sources(self):
        """
        Return a list of current URLs that are directly referenced by the repo

        :return:
            A list of URLs and/or file paths
        """

        if not self.fetch_and_validate():
            return []

        output = [self.repo]
        if self.schema_major_version >= 2:
            for package in self.repo_info['packages']:
                details = package.get('details')
                if details:
                    output.append(details)
        return output

    def get_renamed_packages(self):
        """:return: A dict of the packages that have been renamed"""

        if not self.fetch_and_validate():
            return {}

        if self.schema_major_version < 2:
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
