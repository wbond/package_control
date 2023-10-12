import json
import re
import os
from itertools import chain
from urllib.parse import urlparse

from ..clients.bitbucket_client import BitBucketClient
from ..clients.client_exception import ClientException
from ..clients.github_client import GitHubClient
from ..clients.gitlab_client import GitLabClient
from ..console_write import console_write
from ..download_manager import http_get, resolve_url, resolve_urls, update_url
from ..downloaders.downloader_exception import DownloaderException
from ..package_version import version_sort
from .base_repository_provider import BaseRepositoryProvider
from .provider_exception import ProviderException
from .schema_version import SchemaVersion


class InvalidRepoFileException(ProviderException):
    def __init__(self, repo, reason_message):
        super().__init__(
            'Repository {} does not appear to be a valid repository file because'
            ' {}'.format(repo.repo_url, reason_message))


class InvalidLibraryReleaseKeyError(ProviderException):
    def __init__(self, repo, name, key):
        super().__init__(
            'Invalid or missing release-level key "{}" in library "{}"'
            ' in repository "{}".'.format(key, name, repo))


class InvalidPackageReleaseKeyError(ProviderException):
    def __init__(self, repo, name, key):
        super().__init__(
            'Invalid or missing release-level key "{}" in package "{}"'
            ' in repository "{}".'.format(key, name, repo))


class JsonRepositoryProvider(BaseRepositoryProvider):
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
        self.included_urls = set()
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

        if self.repo_info is not None:
            return True

        if self.repo_url in self.failed_sources:
            return False

        try:
            self.repo_info = self.fetch_repo(self.repo_url)
            self.schema_version = self.repo_info['schema_version']
        except (DownloaderException, ClientException, ProviderException) as e:
            self.failed_sources[self.repo_url] = e
            self.libraries = {}
            self.packages = {}
            return False

        return True

    def fetch_repo(self, location):
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

        # Prevent circular includes
        if location in self.included_urls:
            raise ProviderException('Error, repository "%s" already included.' % location)

        self.included_urls.add(location)

        if re.match(r'https?://', location, re.I):
            json_string = http_get(location, self.settings, 'Error downloading repository.')

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
            schema_version = repo_info['schema_version'] = SchemaVersion(repo_info['schema_version'])
        except KeyError:
            raise InvalidRepoFileException(
                self, 'the "schema_version" JSON key is missing.')
        except ValueError as e:
            raise InvalidRepoFileException(self, e)

        # Main keys depending on scheme version
        if schema_version.major < 4:
            repo_keys = {'packages', 'dependencies', 'includes'}
        else:
            repo_keys = {'packages', 'libraries', 'includes'}

        # Check existence of at least one required main key
        if not set(repo_info.keys()) & repo_keys:
            raise InvalidRepoFileException(self, 'it doesn\'t look like a repository.')

        # Check type of existing main keys
        for key in repo_keys:
            if key in repo_info and not isinstance(repo_info[key], list):
                raise InvalidRepoFileException(self, 'the "%s" key is not an array.' % key)

        # Migrate dependencies to libraries
        # The 4.0.0 repository schema renamed dependencies key to libraries.
        if schema_version.major < 4:
            repo_info['libraries'] = repo_info.pop('dependencies', [])

        # Allow repositories to include other repositories, recursively
        includes = repo_info.pop('includes', None)
        if includes:
            for include in resolve_urls(self.repo_url, includes):
                try:
                    include_info = self.fetch_repo(include)
                except (DownloaderException, ClientException, ProviderException) as e:
                    self.failed_sources[include] = e
                else:
                    include_version = include_info['schema_version']
                    if include_version != schema_version:
                        raise ProviderException(
                            'Scheme version of included repository %s doesn\'t match its parent.' % include)

                    repo_info['packages'].extend(include_info.get('packages', []))
                    repo_info['libraries'].extend(include_info.get('libraries', []))

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

        if self.libraries is not None:
            for key, value in self.libraries.items():
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

        required_library_keys = {
            'description', 'author', 'issues', 'releases'
        }

        copied_library_keys = ('name', 'description', 'author', 'issues')
        copied_release_keys = ('date', 'version', 'sha256')
        default_platforms = ['*']
        default_python_versions = ['3.3']
        default_sublime_text = '*'

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

            for field in copied_library_keys:
                field_value = library.get(field)
                if field_value:
                    info[field] = field_value

            if 'name' not in info:
                self.failed_sources[self.repo_url] = ProviderException(
                    'No "name" value for one of libraries'
                    ' in repository "{}".'.format(self.repo_url)
                )
                continue

            try:
                unknown_keys = set(library) - allowed_library_keys
                if unknown_keys:
                    raise ProviderException(
                        'The "{}" key(s) in library "{}" in repository {} are not supported.'.format(
                            '", "'.join(sorted(unknown_keys)), info['name'],
                            self.repo_url
                        )
                    )

                releases = library.get('releases', [])
                if releases and not isinstance(releases, list):
                    raise ProviderException(
                        'The "releases" value is not an array for library "{}"'
                        ' in repository {}.'.format(info['name'], self.repo_url)
                    )

                for release in releases:
                    download_info = {}

                    unknown_keys = set(release) - allowed_release_keys
                    if unknown_keys:
                        raise ProviderException(
                            'The "{}" key(s) in one of the releases of library "{}"'
                            ' in repository {} are not supported.'.format(
                                '", "'.join(sorted(unknown_keys)), info['name'], self.repo_url
                            )
                        )

                    # Validate libraries
                    # the key can be used to specify dependencies, upstream via repositories
                    key = 'libraries' if self.schema_version.major >= 4 else 'dependencies'
                    value = release.get(key, [])
                    if value:
                        if not isinstance(value, list):
                            raise InvalidLibraryReleaseKeyError(self.repo_url, info['name'], key)
                        download_info['libraries'] = value

                    # Validate supported platforms
                    key = 'platforms'
                    value = release.get(key, default_platforms)
                    if isinstance(value, str):
                        value = [value]
                    elif not isinstance(value, list):
                        raise InvalidLibraryReleaseKeyError(self.repo_url, info['name'], key)
                    download_info[key] = value

                    # Validate supported python_versions
                    key = 'python_versions'
                    value = release.get(key, default_python_versions)
                    if isinstance(value, str):
                        value = [value]
                    elif not isinstance(value, list):
                        raise InvalidLibraryReleaseKeyError(self.repo_url, info['name'], key)
                    download_info[key] = value

                    # Validate supported ST version
                    key = 'sublime_text'
                    value = release.get(key, default_sublime_text)
                    if not isinstance(value, str):
                        raise InvalidLibraryReleaseKeyError(self.repo_url, info['name'], key)
                    download_info[key] = value

                    # Validate url
                    # if present, it is an explicit or resolved release
                    url = release.get('url')
                    if url:
                        for key in copied_release_keys:
                            if key in release:
                                value = release[key]
                                if not value or not isinstance(value, str):
                                    raise InvalidLibraryReleaseKeyError(self.repo_url, info['name'], key)
                                download_info[key] = value

                        if 'version' not in download_info:
                            raise ProviderException(
                                'Missing "version" key in release with explicit "url" of library "{}"'
                                ' in repository "%s".'.format(info['name'], self.repo_url)
                            )

                        download_info['url'] = update_url(resolve_url(self.repo_url, url), debug)
                        is_http = urlparse(download_info['url']).scheme == 'http'
                        if is_http and 'sha256' not in download_info:
                            raise ProviderException(
                                'No "sha256" key for the non-secure "url" value in one of the releases'
                                ' of the library "{}" in repository {}.'.format(info['name'], self.repo_url)
                            )

                        info['releases'].append(download_info)
                        continue

                    # Resolve release template using `base` and `branch` or `tags` keys

                    base = release.get('base')
                    if not base:
                        raise InvalidLibraryReleaseKeyError(self.repo_url, info['name'], 'base')

                    base_url = resolve_url(self.repo_url, base)
                    downloads = None

                    # Evaluate and resolve "tags" and "branch" release templates
                    tags = release.get('tags')
                    branch = release.get('branch')

                    if tags:
                        extra = None
                        if tags is not True:
                            extra = tags
                        for client in clients:
                            downloads = client.download_info_from_tags(base_url, extra)
                            if downloads is not None:
                                break

                    elif branch:
                        for client in clients:
                            downloads = client.download_info_from_branch(base_url, branch)
                            if downloads is not None:
                                break
                    else:
                        raise ProviderException(
                            'Missing "branch", "tags" or "url" key in release of library "{}"'
                            ' in repository "%s".'.format(info['name'], self.repo_url)
                        )

                    if downloads is None:
                        raise ProviderException(
                            'Invalid "base" value "{}" for one of the releases of library "{}"'
                            ' in repository "{}".'.format(base, info['name'], self.repo_url)
                        )

                    if downloads is False:
                        raise ProviderException(
                            'No valid semver tags found at "{}" for library "{}"'
                            ' in repository "{}".'.format(base, info['name'], self.repo_url)
                        )

                    for download in downloads:
                        download.update(download_info)
                        info['releases'].append(download)

                # check required library keys
                for key in required_library_keys:
                    if not info.get(key):
                        raise ProviderException(
                            'Missing or invalid "{}" key for library "{}"'
                            ' in repository "{}".'.format(key, info['name'], self.repo_url)
                        )

                info['releases'] = version_sort(info['releases'], 'platforms', reverse=True)

                output[info['name']] = info
                yield (info['name'], info)

            except (DownloaderException, ClientException, ProviderException) as e:
                self.broken_libriaries[info['name']] = e

        self.libraries = output

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
                    'previous_names': [old_name, ...],
                    'labels': [label, ...],
                    'sources': [url, ...],
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

        if self.packages is not None:
            for key, value in self.packages.items():
                yield (key, value)
            return

        if invalid_sources is not None and self.repo_url in invalid_sources:
            return

        if not self.fetch():
            return

        required_package_keys = {'author', 'releases'}

        copied_package_keys = (
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
        )
        copied_release_keys = ('date', 'version')
        default_platforms = ['*']
        default_sublime_text = '*'

        debug = self.settings.get('debug')

        clients = [
            Client(self.settings) for Client in (GitHubClient, GitLabClient, BitBucketClient)
        ]

        output = {}
        for package in self.repo_info['packages']:
            info = {
                'releases': [],
                'sources': [self.repo_url]
            }

            for field in copied_package_keys:
                if package.get(field):
                    info[field] = package.get(field)

            # Try to grab package-level details from GitHub or BitBucket
            details = package.get('details')
            if details:
                details = resolve_url(self.repo_url, details)

                if invalid_sources is not None and details in invalid_sources:
                    continue

                if details not in info['sources']:
                    info['sources'].append(details)

                try:
                    repo_info = None

                    for client in clients:
                        repo_info = client.repo_info(details)
                        if repo_info:
                            break
                    else:
                        raise ProviderException(
                            'Invalid "details" value "{}" for one of the packages'
                            ' in the repository {}.'.format(details, self.repo_url)
                        )

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
                self.failed_sources[self.repo_url] = ProviderException(
                    'No "name" value for one of the packages'
                    ' in the repository {}.'.format(self.repo_url)
                )
                continue

            try:
                # evaluate releases

                releases = package.get('releases')

                if self.schema_version.major == 2:
                    # If no releases info was specified, also grab the download info from GH or BB
                    if not releases and details:
                        releases = [{'details': details}]

                if not releases:
                    raise ProviderException(
                        'No "releases" value for the package "{}"'
                        ' in the repository {}.'.format(info['name'], self.repo_url)
                    )

                if not isinstance(releases, list):
                    raise ProviderException(
                        'The "releases" value is not an array for the package "{}"'
                        ' in the repository {}.'.format(info['name'], self.repo_url)
                    )

                # This allows developers to specify a GH or BB location to get releases from,
                # especially tags URLs (https://github.com/user/repo/tags or
                # https://bitbucket.org/user/repo#tags)
                for release in releases:
                    download_info = {}

                    # Validate libraries
                    # the key can be used to specify dependencies, upstream via repositories
                    key = 'libraries' if self.schema_version.major >= 4 else 'dependencies'
                    value = release.get(key, [])
                    if value:
                        if not isinstance(value, list):
                            raise InvalidPackageReleaseKeyError(self.repo_url, info['name'], key)
                        download_info['libraries'] = value

                    # Validate supported platforms
                    key = 'platforms'
                    value = release.get(key, default_platforms)
                    if isinstance(value, str):
                        value = [value]
                    elif not isinstance(value, list):
                        raise InvalidPackageReleaseKeyError(self.repo_url, info['name'], key)
                    download_info[key] = value

                    # Validate supported python_versions
                    if self.schema_version.major >= 4:
                        key = 'python_versions'
                        value = release.get(key)
                        if value:
                            # Package releases may optionally contain `python_versions` list to tell
                            # which python version they are compatibilible with.
                            # The main purpose is to be able to opt-in unmaintained packages to python 3.8
                            # if they are known not to cause trouble.
                            if isinstance(value, str):
                                value = [value]
                            elif not isinstance(value, list):
                                raise InvalidPackageReleaseKeyError(self.repo_url, info['name'], key)
                            download_info[key] = value

                    if self.schema_version.major >= 3:
                        # Validate supported ST version
                        # missing key indicates any ST3+ build is supported
                        key = 'sublime_text'
                        value = release.get(key, default_sublime_text)
                        if not isinstance(value, str):
                            raise InvalidPackageReleaseKeyError(self.repo_url, info['name'], key)
                        download_info[key] = value

                        # Validate url
                        # if present, it is an explicit or resolved release
                        url = release.get('url')
                        if url:
                            # Validate date and version
                            for key in copied_release_keys:
                                if key in release:
                                    value = release[key]
                                    if not value or not isinstance(value, str):
                                        raise InvalidPackageReleaseKeyError(self.repo_url, info['name'], key)
                                    download_info[key] = value

                            if 'version' not in download_info:
                                raise ProviderException(
                                    'Missing "version" key in release with explicit "url" of package "{}"'
                                    ' in repository "%s".'.format(info['name'], self.repo_url)
                                )

                            download_info['url'] = update_url(resolve_url(self.repo_url, url), debug)
                            info['releases'].append(download_info)
                            continue

                        # Resolve release template using `base` and `branch` or `tags` keys

                        base = release.get('base')
                        if not base:
                            base = details
                        if not base:
                            raise ProviderException(
                                'Missing root-level "details" key, or release-level "base" key'
                                ' for one of the releases of package "{}"'
                                ' in repository {}.'.format(info['name'], self.repo_url)
                            )

                        base_url = resolve_url(self.repo_url, base)
                        downloads = None

                        tags = release.get('tags')
                        branch = release.get('branch')

                        if tags:
                            extra = None
                            if tags is not True:
                                extra = tags
                            for client in clients:
                                downloads = client.download_info_from_tags(base_url, extra)
                                if downloads is not None:
                                    break
                        elif branch:
                            for client in clients:
                                downloads = client.download_info_from_branch(base_url, branch)
                                if downloads is not None:
                                    break
                        else:
                            raise ProviderException(
                                'Missing "branch", "tags" or "url" key in release of package "{}"'
                                ' in repository "%s".'.format(info['name'], self.repo_url)
                            )

                        if downloads is None:
                            raise ProviderException(
                                'Invalid "base" value "{}" for one of the releases of package "{}"'
                                ' in repository "{}".'.format(base, info['name'], self.repo_url)
                            )

                        if downloads is False:
                            raise ProviderException(
                                'No valid semver tags found at "{}" for package "{}"'
                                ' in repository "{}".'.format(base, info['name'], self.repo_url)
                            )

                        for download in downloads:
                            download.update(download_info)
                            info['releases'].append(download)

                    elif self.schema_version.major == 2:
                        # missing key indicates ST2 release; no longer supported
                        key = 'sublime_text'
                        value = release.get(key)
                        if not value:
                            continue
                        if not isinstance(value, str):
                            raise InvalidPackageReleaseKeyError(self.repo_url, info['name'], key)
                        download_info[key] = value

                        # Validate url
                        # if present, it is an explicit or resolved release
                        url = release.get('url')
                        if url:
                            for key in copied_release_keys:
                                if key in release:
                                    value = release[key]
                                    if not value or not isinstance(value, str):
                                        raise InvalidPackageReleaseKeyError(self.repo_url, info['name'], key)
                                    download_info[key] = value

                            if 'version' not in download_info:
                                raise ProviderException(
                                    'Missing "version" key in release with explicit "url" of package "{}"'
                                    ' in repository "%s".'.format(info['name'], self.repo_url)
                                )

                            download_info['url'] = update_url(resolve_url(self.repo_url, url), debug)
                            info['releases'].append(download_info)
                            continue

                        # Evaluate and resolve "tags" and "branch" release templates

                        download_details = release.get('details')
                        if not download_details or not isinstance(download_details, str):
                            raise InvalidPackageReleaseKeyError(self.repo_url, info['name'], 'details')

                        download_details = resolve_url(self.repo_url, release['details'])

                        downloads = None

                        for client in clients:
                            downloads = client.download_info(download_details)
                            if downloads is not None:
                                break

                        if downloads is None:
                            raise ProviderException(
                                'Invalid "details" value "{}" for one of the releases of package "{}"'
                                ' in repository "{}".'.format(download_details, info['name'], self.repo_url)
                            )

                        if downloads is False:
                            raise ProviderException(
                                'No valid semver tags found at "{}" for package "{}"'
                                ' in repository "{}".'.format(download_details, info['name'], self.repo_url)
                            )

                        for download in downloads:
                            download.update(download_info)
                            info['releases'].append(download)

                # check required package keys
                for key in required_package_keys:
                    if not info.get(key):
                        raise ProviderException(
                            'Missing or invalid "{}" key for package "{}"'
                            ' in repository "{}".'.format(key, info['name'], self.repo_url)
                        )

                info['releases'] = version_sort(info['releases'], 'platforms', reverse=True)

                for field in ('previous_names', 'labels'):
                    if field not in info:
                        info[field] = []

                if 'readme' in info:
                    info['readme'] = update_url(resolve_url(self.repo_url, info['readme']), debug)

                for field in ('description', 'readme', 'issues', 'donate', 'buy'):
                    if field not in info:
                        info[field] = None

                if 'homepage' not in info:
                    info['homepage'] = details if details else self.repo_url

                if 'last_modified' not in info:
                    # Extract a date from the newest release
                    date = '1970-01-01 00:00:00'
                    for release in info['releases']:
                        release_date = release.get('date')
                        if release_date and isinstance(release_date, str) and release_date > date:
                            date = release_date
                    info['last_modified'] = date

                output[info['name']] = info
                yield (info['name'], info)

            except (DownloaderException, ClientException, ProviderException) as e:
                self.broken_packages[info['name']] = e

        self.packages = output

    def get_sources(self):
        """
        Return a list of current URLs that are directly referenced by the repo

        :return:
            A list of URLs and/or file paths
        """

        if not self.fetch():
            return []

        output = [self.repo_url]
        for package in self.repo_info['packages']:
            details = package.get('details')
            if details:
                output.append(details)
        return output

    def get_renamed_packages(self):
        """:return: A dict of the packages that have been renamed"""

        if not self.fetch():
            return {}

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
