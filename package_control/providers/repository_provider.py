import json
import re
import os
from itertools import chain
from urllib.parse import urljoin, urlparse

from .. import text
from ..clients.bitbucket_client import BitBucketClient
from ..clients.client_exception import ClientException
from ..clients.github_client import GitHubClient
from ..clients.gitlab_client import GitLabClient
from ..console_write import console_write
from ..download_manager import downloader, update_url
from ..downloaders.downloader_exception import DownloaderException
from ..versions import version_sort
from .base_repository_provider import BaseRepositoryProvider
from .provider_exception import ProviderException
from .schema_compat import platforms_to_releases
from .schema_compat import SchemaVersion


class InvalidRepoFileException(ProviderException):

    def __init__(self, repo, reason_message):
        super().__init__(
            'Repository %s does not appear to be a valid repository file because'
            ' %s' % (repo.repo_url, reason_message))


class RepositoryProvider(BaseRepositoryProvider):
    """
    Generic repository downloader that fetches package info

    With the current channel/repository architecture where the channel file
    caches info from all includes repositories, these package providers just
    serve the purpose of downloading packages not in the default channel.

    The structure of the JSON a repository should contain is located in
    example-packages.json.

    :param repo_url:
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
          `query_string_params`,
          `http_basic_auth`
    """

    def __init__(self, repo_url, settings):
        super().__init__(repo_url, settings)
        self.repo_info = None
        self.schema_version = None

    def fetch(self):
        """
        Retrieves and loads the JSON for other methods to use

        :raises:
            InvalidChannelFileException: when parsing or validation file content fails
            ProviderException: when an error occurs trying to open a file
            DownloaderException: when an error occurs trying to open a URL
        """

        if self.repo_url in self.failed_sources:
            return False

        if self.repo_info is not None:
            return True

        try:
            self.fetch_repo()
        except (DownloaderException, ProviderException) as e:
            self.failed_sources[self.repo_url] = e
            self.cache['get_libraries'] = {}
            self.cache['get_packages'] = {}
            return False

        return True

    def fetch_repo(self):
        self.cache = {}
        self.repo_info = self.fetch_json(self.repo_url)
        self.schema_version = self.repo_info['schema_version']

        # The 4.0.0 repository schema renamed dependencies key to libraries.
        if self.schema_version.major < 4:
            self.repo_info['libraries'] = self.repo_info.pop('dependencies', [])

        for key in ('packages', 'libraries'):
            if key not in self.repo_info:
                self.repo_info[key] = []

        if 'includes' not in self.repo_info:
            return

        # Allow repositories to include other repositories
        scheme_match = re.match(r'(https?:)//', self.repo_url, re.I)
        if scheme_match is None:
            relative_base = os.path.dirname(self.repo_url)
            is_http = False
        else:
            is_http = True

        for include in self.repo_info.pop('includes', []):
            if include.startswith('//'):
                if scheme_match is not None:
                    include = scheme_match.group(1) + include
                else:
                    include = 'https:' + include
            elif include.startswith('/'):
                # We don't allow absolute includes
                continue
            elif include.startswith('./') or include.startswith('../'):
                if is_http:
                    include = urljoin(self.repo_url, include)
                else:
                    include = os.path.join(relative_base, include)
                    include = os.path.normpath(include)

            include_info = self.fetch_json(include)
            include_version = include_info['schema_version']
            if include_version != self.schema_version:
                raise ProviderException(
                    'Scheme version of included repository %s doesn\'t match its parent.' % include)

            included_packages = include_info.get('packages', [])
            self.repo_info['packages'].extend(included_packages)

            # The 4.0.0 repository schema renamed dependencies key to libraries.
            libraries_key = 'libraries' if include_version.major >= 4 else 'dependencies'
            included_libraries = include_info.get(libraries_key, [])
            self.repo_info['libraries'].extend(included_libraries)

    def fetch_json(self, location):
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

        if re.match(r'https?://', location, re.I):
            with downloader(location, self.settings) as manager:
                json_string = manager.fetch(location, 'Error downloading repository.')

        # Anything that is not a URL is expected to be a filesystem path
        else:
            if not os.path.exists(location):
                raise ProviderException('Error, file %s does not exist' % location)

            if self.settings.get('debug'):
                console_write(
                    '''
                    Loading %s as a repository
                    ''',
                    location
                )

            # We open as binary so we get bytes like the DownloadManager
            with open(location, 'rb') as f:
                json_string = f.read()

        try:
            repo_info = json.loads(json_string.decode('utf-8'))
        except (ValueError):
            raise InvalidRepoFileException(self, 'parsing JSON failed.')

        try:
            repo_info['schema_version'] = SchemaVersion(repo_info['schema_version'])
        except KeyError:
            raise InvalidRepoFileException(
                self, 'the "schema_version" JSON key is missing.')
        except ValueError as e:
            raise InvalidRepoFileException(self, e)

        if isinstance(repo_info['packages'], dict):
            raise InvalidRepoFileException(
                self,
                'the "packages" key is an object, not an array. '
                'This indicates it is a channel not a repository.')

        return repo_info

    def get_libraries(self, invalid_sources=None):
        """
        Provides access to the libraries in this repository

        :param invalid_sources:
            A list of URLs that are permissible to fetch data from

        :return:
            A generator of
            (
                'Library Name',
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
                            'python_versions': ['3.3', '3.8'],
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

        if 'get_libraries' in self.cache:
            for key, value in self.cache['get_libraries'].items():
                yield (key, value)
            return

        if invalid_sources is not None and self.repo_url in invalid_sources:
            return

        if not self.fetch():
            return

        if self.schema_version.major >= 4:
            allowed_library_keys = {
                'name', 'description', 'author', 'issues', 'releases'
            }
            allowed_release_keys = {  # todo: remove 'branch'
                'base', 'version', 'sublime_text', 'platforms', 'python_versions', 'branch', 'tags', 'url', 'sha256'
            }
        else:
            allowed_library_keys = {
                'name', 'description', 'author', 'issues', 'load_order', 'releases'
            }
            allowed_release_keys = {
                'base', 'version', 'sublime_text', 'platforms', 'branch', 'tags', 'url', 'sha256'
            }

        debug = self.settings.get('debug')

        clients = [
            Client(self.settings) for Client in (GitHubClient, GitLabClient, BitBucketClient)
        ]

        output = {}
        for library in self.repo_info['libraries']:
            info = {
                'releases': [],
                'sources': [self.repo_url]
            }

            for field in ('name', 'description', 'author', 'issues'):
                field_value = library.get(field)
                if field_value:
                    info[field] = field_value

            if 'name' not in info:
                self.failed_sources[self.repo_url] = ProviderException(text.format(
                    '''
                    No "name" value for one of the libraries in the repository %s.
                    ''',
                    self.repo_url
                ))
                continue

            try:
                unknown_keys = set(library) - allowed_library_keys
                if unknown_keys:
                    raise ProviderException(text.format(
                        '''
                        The "%s" key(s) in the library "%s" in the repository %s are not supported.
                        ''',
                        ('", "'.join(sorted(unknown_keys)), info['name'], self.repo_url)
                    ))

                releases = library.get('releases', [])
                if releases and not isinstance(releases, list):
                    raise ProviderException(text.format(
                        '''
                        The "releases" value is not an array for the library "%s" in the repository %s.
                        ''',
                        (info['name'], self.repo_url)
                    ))

                def assert_release_keys(download_info):
                    for key in ('version', 'url', 'sublime_text', 'platforms', 'python_versions'):
                        if key not in download_info:
                            raise ProviderException(text.format(
                                '''
                                Missing "%s" key for one of the releases of the library "%s" in the repository %s.
                                ''',
                                (key, info['name'], self.repo_url)
                            ))

                for release in releases:
                    download_info = {}

                    unknown_keys = set(release) - allowed_release_keys
                    if unknown_keys:
                        raise ProviderException(text.format(
                            '''
                            The "%s" key(s) in one of the releases of the library "%s"
                            in the repository %s are not supported.
                            ''',
                            ('", "'.join(sorted(unknown_keys)), info['name'], self.repo_url)
                        ))

                    # Make sure that explicit fields are copied over
                    for field in ('sublime_text', 'version', 'sha256'):
                        value = release.get(field)
                        if value:
                            download_info[field] = value

                    # Validate url
                    value = release.get('url')
                    if value:
                        download_info['url'] = update_url(value, debug)

                    # Validate supported platforms
                    value = release.get('platforms', ['*'])
                    if not isinstance(value, list):
                        value = [value]
                    download_info['platforms'] = value

                    # Validate supported python_versions
                    if self.schema_version.major < 4:
                        # Assume python 3.3 for backward compatibility with older schemes.
                        # Note: ST2 with python 2.6 are no longer supported
                        download_info['python_versions'] = ['3.3']
                    else:
                        value = release.get('python_versions')
                        if value:
                            if not isinstance(value, list):
                                value = [value]
                            download_info['python_versions'] = value

                    tags = release.get('tags')
                    branch = release.get('branch')

                    if tags or branch:
                        base = None
                        if 'base' in release:
                            base = release['base']

                        if not base:
                            raise ProviderException(text.format(
                                '''
                                Missing release-level "base" key for one of the releases of the
                                library "%s" in the repository %s.
                                ''',
                                (info['name'], self.repo_url)
                            ))

                        client = None
                        extra = None
                        url = None

                        if tags:
                            if tags is not True:
                                extra = tags
                            for client in clients:
                                url = client.make_tags_url(base)
                                if url:
                                    break

                        if branch:
                            for client in clients:
                                url = client.make_branch_url(base, branch)
                                if url:
                                    break

                        if not url:
                            raise ProviderException(text.format(
                                '''
                                Invalid "base" value "%s" for one of the releases of the
                                library "%s" in the repository %s.
                                ''',
                                (base, info['name'], self.repo_url)
                            ))

                        downloads = client.download_info(url, extra)
                        if downloads is False:
                            raise ProviderException(text.format(
                                '''
                                No valid semver tags found at %s for the library
                                "%s" in the repository %s.
                                ''',
                                (url, info['name'], self.repo_url)
                            ))

                        for download in downloads:
                            del download['date']
                            new_download = download_info.copy()
                            new_download.update(download)
                            assert_release_keys(new_download)
                            info['releases'].append(new_download)

                    elif 'url' in download_info:
                        is_http = urlparse(download_info['url']).scheme == 'http'
                        if is_http and 'sha256' not in download_info:
                            raise ProviderException(text.format(
                                '''
                                No "sha256" key for the non-secure "url" value in one of the
                                releases of the library "%s" in the repository %s.
                                ''',
                                (info['name'], self.repo_url)
                            ))

                        assert_release_keys(download_info)
                        info['releases'].append(download_info)

                # check required library keys
                for key in ('author', 'releases', 'issues', 'description'):
                    if key not in info:
                        raise ProviderException(text.format(
                            '''
                            No "%s" key for the library "%s" in the repository %s.
                            ''',
                            (key, info['name'], self.repo_url)
                        ))

                info['releases'] = version_sort(info['releases'], 'platforms', reverse=True)

                output[info['name']] = info
                yield (info['name'], info)

            except (DownloaderException, ClientException, ProviderException) as e:
                self.broken_libriaries[info['name']] = e

        self.cache['get_libraries'] = output

    def get_packages(self, invalid_sources=None):
        """
        Provides access to the packages in this repository

        :param invalid_sources:
            A list of URLs that are permissible to fetch data from

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
                            'libraries': [library name, ...]
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

        if invalid_sources is not None and self.repo_url in invalid_sources:
            return

        if not self.fetch():
            return

        debug = self.settings.get('debug')

        clients = [
            Client(self.settings) for Client in (GitHubClient, GitLabClient, BitBucketClient)
        ]

        # Backfill the "previous_names" keys for old schemas
        previous_names = {}
        if self.schema_version.major < 2:
            renamed = self.get_renamed_packages()
            for old_name in renamed:
                new_name = renamed[old_name]
                if new_name not in previous_names:
                    previous_names[new_name] = []
                previous_names[new_name].append(old_name)

        output = {}
        for package in self.repo_info['packages']:
            info = {
                'sources': [self.repo_url]
            }

            copy_fields = [
                'name',
                'description',
                'author',
                'last_modified',
                'previous_names',
                'labels',
                'homepage',
                'readme',
                'issues',
                'donate',
                'buy'
            ]
            for field in copy_fields:
                if package.get(field):
                    info[field] = package.get(field)

            # Schema version 2.0 allows for grabbing details about a package, or its
            # download from "details" urls. See the GitHubClient and BitBucketClient
            # classes for valid URLs.
            if self.schema_version.major >= 2:
                details = package.get('details')
                releases = package.get('releases')

                # Try to grab package-level details from GitHub or BitBucket
                if details:
                    if invalid_sources is not None and details in invalid_sources:
                        continue

                    info['sources'].append(details)

                    try:
                        repo_info = None

                        for client in clients:
                            repo_info = client.repo_info(details)
                            if repo_info:
                                break
                        else:
                            raise ProviderException(text.format(
                                '''
                                Invalid "details" value "%s" for one of the packages in the repository %s.
                                ''',
                                (details, self.repo_url)
                            ))

                        del repo_info['default_branch']

                        # When grabbing details, prefer explicit field values over the values
                        # from the GitHub or BitBucket API
                        info = dict(chain(repo_info.items(), info.items()))

                    except (DownloaderException, ClientException, ProviderException) as e:
                        if 'name' in info:
                            self.broken_packages[info['name']] = e
                        self.failed_sources[details] = e
                        continue

            if 'name' not in info:
                self.failed_sources[self.repo_url] = ProviderException(text.format(
                    '''
                    No "name" value for one of the packages in the repository %s.
                    ''',
                    self.repo_url
                ))
                continue

            info['releases'] = []
            if self.schema_version.major == 2:
                # If no releases info was specified, also grab the download info from GH or BB
                if not releases and details:
                    releases = [{'details': details}]

            if self.schema_version.major >= 2:
                if not releases:
                    e = ProviderException(text.format(
                        '''
                        No "releases" value for the package "%s" in the repository %s.
                        ''',
                        (info['name'], self.repo_url)
                    ))
                    self.broken_packages[info['name']] = e
                    continue

                if not isinstance(releases, list):
                    e = ProviderException(text.format(
                        '''
                        The "releases" value is not an array or the package "%s" in the repository %s.
                        ''',
                        (info['name'], self.repo_url)
                    ))
                    self.broken_packages[info['name']] = e
                    continue

                # This allows developers to specify a GH or BB location to get releases from,
                # especially tags URLs (https://github.com/user/repo/tags or
                # https://bitbucket.org/user/repo#tags)
                for release in releases:
                    download_details = None
                    download_info = {}

                    # Make sure that explicit fields are copied over
                    for field in ['platforms', 'sublime_text', 'version', 'url', 'date', 'libraries']:
                        if field in release:
                            value = release[field]
                            if field == 'url':
                                value = update_url(value, debug)
                            if field == 'platforms' and not isinstance(release['platforms'], list):
                                value = [value]
                            download_info[field] = value

                    if self.schema_version.major < 4 and 'dependencies' in release:
                        download_info['libraries'] = release['dependencies']

                    if 'platforms' not in download_info:
                        download_info['platforms'] = ['*']

                    if self.schema_version.major == 2:
                        if 'sublime_text' not in download_info:
                            download_info['sublime_text'] = '<3000'

                        if 'details' in release:
                            download_details = release['details']

                            try:
                                downloads = False

                                for client in clients:
                                    downloads = client.download_info(download_details)
                                    if downloads is not None:
                                        break

                                if downloads is False:
                                    raise ProviderException(text.format(
                                        '''
                                        Invalid "details" value "%s" under the "releases" key
                                        for the package "%s" in the repository %s.
                                        ''',
                                        (download_details, info['name'], self.repo_url)
                                    ))

                                for download in downloads:
                                    new_download = download_info.copy()
                                    new_download.update(download)
                                    info['releases'].append(new_download)

                            except (DownloaderException, ClientException, ProviderException) as e:
                                self.broken_packages[info['name']] = e

                        elif download_info:
                            info['releases'].append(download_info)

                    elif self.schema_version.major >= 3:
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
                                    raise ProviderException(text.format(
                                        '''
                                        Missing root-level "details" key, or release-level "base" key
                                        for one of the releases of the package "%s" in the repository %s.
                                        ''',
                                        (info['name'], self.repo_url)
                                    ))

                                client = None
                                extra = None
                                url = None

                                if tags:
                                    if tags is not True:
                                        extra = tags
                                    for client in clients:
                                        url = client.make_tags_url(base)
                                        if url:
                                            break

                                if branch:
                                    for client in clients:
                                        url = client.make_branch_url(base, branch)
                                        if url:
                                            break

                                if not url:
                                    raise ProviderException(text.format(
                                        '''
                                        Invalid "base" value "%s" for one of the releases of the
                                        package "%s" in the repository %s.
                                        ''',
                                        (base, info['name'], self.repo_url)
                                    ))

                                downloads = client.download_info(url, extra)
                                if downloads is False:
                                    raise ProviderException(text.format(
                                        '''
                                        No valid semver tags found at %s for the
                                        package "%s" in the repository %s.
                                        ''',
                                        (url, info['name'], self.repo_url)
                                    ))

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
                self.broken_packages[info['name']] = ProviderException(text.format(
                    '''
                    No "author" key for the package "%s" in the repository %s.
                    ''',
                    (info['name'], self.repo_url)
                ))
                continue

            if 'releases' not in info:
                self.broken_packages[info['name']] = ProviderException(text.format(
                    '''
                    No "releases" key for the package "%s" in the repository %s.
                    ''',
                    (info['name'], self.repo_url)
                ))
                continue

            # Make sure all releases have the appropriate keys. We use a
            # function here so that we can break out of multiple loops.
            def has_broken_release():
                for release in info.get('releases', []):
                    for key in ['version', 'date', 'url', 'sublime_text', 'platforms']:
                        if key not in release:
                            self.broken_packages[info['name']] = ProviderException(text.format(
                                '''
                                Missing "%s" key for one of the releases of the package "%s" in the repository %s.
                                ''',
                                (key, info['name'], self.repo_url)
                            ))
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
                info['homepage'] = self.repo_url

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

        if not self.fetch():
            return []

        output = [self.repo_url]
        if self.schema_version.major >= 2:
            for package in self.repo_info['packages']:
                details = package.get('details')
                if details:
                    output.append(details)
        return output

    def get_renamed_packages(self):
        """:return: A dict of the packages that have been renamed"""

        if not self.fetch():
            return {}

        if self.schema_version.major < 2:
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
