import datetime
import hashlib
import json
# To prevent import errors in thread with datetime
import locale  # noqa
import os
import re
import shutil
import tempfile
import time
import zipfile

from concurrent import futures
from functools import partial
from io import BytesIO
from stat import S_IXUSR
from threading import RLock
from urllib.parse import urlencode

import sublime

from . import __version__
from . import library, pep440, sys_path
from .cache import clear_cache, set_cache, get_cache, merge_cache_under_settings, set_cache_under_settings
from .clear_directory import clear_directory, delete_directory
from .clients.client_exception import ClientException
from .console_write import console_write
from .download_manager import http_get
from .downloaders.downloader_exception import DownloaderException
from .package_io import (
    create_empty_file,
    get_installed_package_path,
    get_package_dir,
    get_package_cache_dir,
    get_package_module_cache_dir,
    list_sublime_package_dirs,
    list_sublime_package_files,
    package_file_exists,
    read_package_file,
    regular_file_exists,
    zip_file_exists,
)
from .package_version import PackageVersion, version_sort
from .providers import CHANNEL_PROVIDERS, REPOSITORY_PROVIDERS
from .providers.channel_provider import UncachedChannelRepositoryError
from .providers.provider_exception import ProviderException
from .selectors import is_compatible_version, is_compatible_platform, get_compatible_platform
from .settings import load_list_setting, pc_settings_filename, preferences_filename
from .upgraders.git_upgrader import GitUpgrader
from .upgraders.hg_upgrader import HgUpgrader


DEFAULT_CHANNEL = 'https://packagecontrol.io/channel_v3.json'
OLD_DEFAULT_CHANNELS = set([
    'https://packagecontrol.io/channel.json',
    'https://sublime.wbond.net/channel.json',
    'https://sublime.wbond.net/repositories.json'
])

ZIP_UNIX_SYSTEM = 3


class PackageManager:

    """
    Allows downloading, creating, installing, upgrading, and deleting packages

    Delegates metadata retrieval to the CHANNEL_PROVIDERS classes.
    Uses VcsUpgrader-based classes for handling git and hg repositories in the
    Packages folder. Downloader classes are utilized to fetch contents of URLs.

    Also handles displaying package messaging, and sending usage information to
    the usage server.
    """

    lock = RLock()

    def __init__(self):
        """
        Constructs a new instance.
        """

        self._available_packages = None
        self._available_libraries = None
        self.session_time = datetime.datetime.now()

        self.settings = {}
        settings = sublime.load_settings(pc_settings_filename())
        setting_names = [
            'auto_migrate',
            'auto_upgrade',
            'auto_upgrade_frequency',
            'auto_upgrade_ignore',
            'cache_length',
            'channels',
            'debug',
            'dirs_to_ignore',
            'downloader_precedence',
            'files_to_ignore',
            'files_to_include',
            'git_binary',
            'git_update_command',
            'hg_binary',
            'hg_update_command',
            'http_basic_auth',
            'http_cache',
            'http_cache_length',
            'http_proxy',
            'https_proxy',
            'ignore_vcs_packages',
            'install_missing',
            'install_prereleases',
            'max_backup_age',
            'package_destination',
            'package_name_map',
            'package_profiles',
            'print_messages',
            'proxy_password',
            'proxy_username',
            'remove_orphaned',
            'remove_orphaned_enviornments',
            'renamed_packages',
            'repositories',
            'submit_url',
            'submit_usage',
            'submit_usage_url',
            'timeout',
            'user_agent'
        ]
        for setting in setting_names:
            value = settings.get(setting)
            if value is not None:
                self.settings[setting] = value

        # https_proxy will inherit from http_proxy unless it is set to a
        # string value or false
        no_https_proxy = self.settings.get('https_proxy') in ["", None]
        if no_https_proxy and self.settings.get('http_proxy'):
            self.settings['https_proxy'] = self.settings.get('http_proxy')
        if self.settings.get('https_proxy') is False:
            self.settings['https_proxy'] = ''

        # Fetch least required information from code hosters to save some time
        # and fetch more packages/libraries before hitting rate limits.
        self.settings['min_api_calls'] = True
        self.settings['max_releases'] = 1

        # We cache these to prevent IPC calls between plugin_host and the main
        # Sublime Text executable
        self.settings['platform'] = sublime.platform()
        self.settings['arch'] = sublime.arch()
        self.settings['version'] = int(sublime.version())

        # Cache some user preferences
        if self.settings['version'] > 4192:
            settings = sublime.load_settings(preferences_filename())
            self.settings['disable_plugin_host_3.3'] = settings.get('disable_plugin_host_3.3', False)
        else:
            self.settings['disable_plugin_host_3.3'] = False

        # Use the cache to see if settings have changed since the last
        # time the package manager was created, and clearing any cached
        # values if they have.
        previous_settings = get_cache('filtered_settings', {})

        # Reduce the settings down to exclude channel info since that will
        # make the settings always different
        filtered_settings = self.settings.copy()
        for key in ('cache', 'package_name_map'):
            if key in filtered_settings:
                del filtered_settings[key]

        if filtered_settings != previous_settings:
            if previous_settings:
                console_write(
                    '''
                    Settings change detected, clearing cache
                    '''
                )
                clear_cache()
            set_cache('filtered_settings', filtered_settings)

    def get_mapped_name(self, package_name):
        """:return: The name of the package after passing through mapping rules"""

        return self.settings.get('package_name_map', {}).get(package_name, package_name)

    def get_metadata(self, package_name):
        """
        Returns the package metadata for an installed package

        :param package_name:
            The name of the package

        :return:
            A dict with the keys:
                version
                url
                description
            or an empty dict on error
        """

        metadata_json = read_package_file(package_name, 'package-metadata.json')
        if metadata_json:
            try:
                return json.loads(metadata_json)
            except (ValueError):
                console_write(
                    '''
                    Failed to parse package metadata for "%s"
                    ''',
                    package_name
                )

        return {}

    def get_libraries(self, package_name):
        """
        Returns a list of libraries for the specified package on the
        current machine

        :param package_name:
            The name of the package

        :return:
            A set of library.Library() objects
        """

        python_version = self.get_python_version(package_name)

        names = None

        lib_info_json = read_package_file(package_name, 'dependencies.json')
        if lib_info_json:
            try:
                names = self.select_libraries(json.loads(lib_info_json))
            except (ValueError):
                console_write(
                    '''
                    Failed to parse the dependencies.json for "%s"
                    ''',
                    package_name
                )

        if names is None:
            metadata = self.get_metadata(package_name)
            # "dependencies" key is for backwards compatibility
            names = metadata.get('libraries', metadata.get('dependencies', []))

        if not names:
            return set()

        return set(library.names_to_libraries(names, python_version))

    def get_python_version(self, package_name):
        """
        Returns the version of python a package runs under

        :param package_name:
            The name of the package

        :return:
            A unicode string of "3.3" or "3.8"
        """
        supported_python_versions = sys_path.python_versions()

        # package runs on latest available python version
        if len(supported_python_versions) == 1 or package_name.lower() == "user":
            return supported_python_versions[-1]

        python_version = read_package_file(package_name, ".python-version")
        if python_version:
            python_version = python_version.strip()
            # if requested version is supported, use it
            if python_version in supported_python_versions:
                return python_version

            # otherwise, use latest python version
            return supported_python_versions[-1]

        # package runs on earliest available python
        return supported_python_versions[0]

    def get_version(self, package_name):
        """
        Determines the current version for a package

        :param package_name:
            The package name
        """

        version = self.get_metadata(package_name).get('version')

        if version:
            return version

        upgrader = self.instantiate_upgrader(package_name)
        if upgrader:
            version = upgrader.latest_commit()
            if version:
                return '%s commit %s' % (upgrader.cli_name, version)

        return 'unknown version'

    def is_compatible(self, package_name):
        """
        Detects if a package is compatible with the current Sublime Text install

        :param package_name:
            A package's name string to check for compatibility

        :return:
            If the package is compatible
        """

        metadata = self.get_metadata(package_name)
        if not metadata:
            # unmanaged or unable to parse meta data
            # can't say something about compatibility, assume the best
            return True

        sublime_text = metadata.get('sublime_text')
        platforms = metadata.get('platforms', [])

        # This indicates the metadata is old, so we assume a match
        if not sublime_text and not platforms:
            return True

        return is_compatible_platform(platforms) and is_compatible_version(sublime_text)

    def is_managed(self, package_name):
        """
        Check if package is managed by Package Control.

        :param package_name:
            A package's name string to check for compatibility

        :return:
            ``True`` If the package is managed, ``False`` otherwise.
        """

        return package_file_exists(package_name, 'package-metadata.json')

    def _is_git_package(self, package_name):
        """
        :param package_name:
            The package name

        :return:
            If the package is installed via git
        """

        git_dir = os.path.join(get_package_dir(package_name), '.git')
        return os.path.isdir(git_dir) or os.path.isfile(git_dir)

    def _is_hg_package(self, package_name):
        """
        :param package_name:
            The package name

        :return:
            If the package is installed via hg
        """

        hg_dir = os.path.join(get_package_dir(package_name), '.hg')
        return os.path.isdir(hg_dir)

    def is_vcs_package(self, package_name):
        """
        If the package is installed via git or hg

        :param package_name:
            The package to check

        :return:
            bool
        """

        return self._is_git_package(package_name) or self._is_hg_package(package_name)

    def instantiate_upgrader(self, package_name):
        """
        Creates an HgUpgrader or GitUpgrader object to run operations on a VCS-
        based package

        :param package_name:
            The name of the package

        :return:
            GitUpgrader, HgUpgrader or None
        """

        if self._is_git_package(package_name):
            return GitUpgrader(
                self.settings['git_binary'],
                self.settings['git_update_command'],
                get_package_dir(package_name),
                self.settings['cache_length'],
                self.settings['debug']
            )

        if self._is_hg_package(package_name):
            return HgUpgrader(
                self.settings['hg_binary'],
                self.settings['hg_update_command'],
                get_package_dir(package_name),
                self.settings['cache_length'],
                self.settings['debug']
            )

        return None

    def select_releases(self, package_name, releases):
        """
        Returns all releases in the list of releases that are compatible with
        the current platform and version of Sublime Text

        :param package_name:
            The name of the package

        :param releases:
            A list of release dicts

        :return:
            A list of release dicts
        """

        install_prereleases = self.settings.get('install_prereleases')
        allow_prereleases = (
            install_prereleases is True
            or isinstance(install_prereleases, list) and package_name in install_prereleases
        )

        return [
            release for release in releases
            if is_compatible_platform(release['platforms'])
            and is_compatible_version(release['sublime_text'])
            and (allow_prereleases or PackageVersion(release['version']).is_final)
        ]

    def select_libraries(self, library_info):
        """
        Takes the a dict from a dependencies.json file and returns the
        library names that are applicable to the current machine

        :param library_info:
            A dict from a dependencies.json file

        :return:
            A list of library names
        """

        platforms = list(library_info.keys())
        platform_selector = get_compatible_platform(platforms)
        if platform_selector:
            platform_library = library_info[platform_selector]

            # Sorting reverse will give us >, < then *
            versions = sorted(platform_library.keys(), reverse=True)
            for version_selector in versions:
                if is_compatible_version(version_selector):
                    return platform_library[version_selector]

        # If there were no matches in the info, but there also weren't any
        # errors, then it just means there are not libraries for this machine
        return []

    def list_repositories(self):
        """
        Returns a master list of all repositories pulled from all sources

        These repositories come from the channels specified in the
        "channels" setting, plus any repositories listed in the
        "repositories" setting.

        :return:
            A list of all available repositories
        """

        cache_ttl = self.settings.get('cache_length', 300)
        channels = self.settings.get('channels', [])
        # create copy to prevent backlash to settings object due to being extended
        repositories = self.settings.get('repositories', []).copy()

        # Update any old default channel URLs users have in their config
        found_default = False
        for channel in channels:
            channel = channel.strip()

            if re.match(r'https?://([^.]+\.)*package-control\.io', channel):
                console_write('Removed malicious channel %s' % channel)
                continue

            if channel in OLD_DEFAULT_CHANNELS:
                if found_default:
                    continue
                found_default = True
                channel = DEFAULT_CHANNEL

            # Caches various info from channels for performance
            cache_key = channel + '.repositories'
            if channel[:8].lower() == "file:///":
                channel_repositories = None
            else:
                channel_repositories = get_cache(cache_key)

            merge_cache_under_settings(self, 'renamed_packages', channel)
            merge_cache_under_settings(self, 'unavailable_packages', channel, list_=True)
            merge_cache_under_settings(self, 'unavailable_libraries', channel, list_=True)

            # If any of the info was not retrieved from the cache, we need to
            # grab the channel to get it
            if channel_repositories is None:

                for provider_class in CHANNEL_PROVIDERS:
                    if provider_class.match_url(channel):
                        provider = provider_class(channel, self.settings)
                        break
                else:
                    continue

                try:
                    channel_repositories = provider.get_repositories()
                    if channel[:8].lower() != "file:///":
                        set_cache(cache_key, channel_repositories, cache_ttl)

                    unavailable_packages = []
                    unavailable_libraries = []

                    for repo in channel_repositories:

                        try:
                            filtered_packages = {}
                            for name, info in provider.get_packages(repo):
                                info['releases'] = self.select_releases(name, info['releases'])
                                if info['releases']:
                                    filtered_packages[name] = info
                                else:
                                    unavailable_packages.append(name)

                            packages_cache_key = repo + '.packages'
                            set_cache(packages_cache_key, filtered_packages, cache_ttl)

                        except UncachedChannelRepositoryError:
                            pass

                        try:
                            filtered_libraries = {}
                            for name, info in provider.get_libraries(repo):
                                # Convert legacy dependency names to official pypi package names.
                                # This is required for forward compatibility with upcomming changes
                                # in scheme 4.0.0. Do it here to apply only on client side.
                                name = info['name'] = library.translate_name(name)

                                info['releases'] = self.select_releases(name, info['releases'])
                                if info['releases']:
                                    dist_name = library.escape_name(name).lower()
                                    filtered_libraries[dist_name] = info
                                else:
                                    unavailable_libraries.append(name)

                            libraries_cache_key = repo + '.libraries'
                            set_cache(libraries_cache_key, filtered_libraries, cache_ttl)

                        except UncachedChannelRepositoryError:
                            pass

                    renamed_packages = provider.get_renamed_packages()
                    set_cache_under_settings(self, 'renamed_packages', channel, renamed_packages, cache_ttl)

                    set_cache_under_settings(
                        self,
                        'unavailable_packages',
                        channel,
                        unavailable_packages,
                        cache_ttl,
                        list_=True
                    )
                    set_cache_under_settings(
                        self,
                        'unavailable_libraries',
                        channel,
                        unavailable_libraries,
                        cache_ttl,
                        list_=True
                    )

                except (DownloaderException, ClientException, ProviderException) as e:
                    console_write(e)
                    continue

            repositories.extend(channel_repositories)

        return [repo.strip() for repo in repositories]

    def fetch_available(self):
        """
        Fetch available packages and libraries from available sources.

        use results from:

        1. in-memory cache (if not out-dated)
        2. http cache (if remote returns 304)
        3. download info from remote and store in caches

        :return:
            Nothing
        """

        if self.settings.get('debug'):
            console_write(
                '''
                Fetching list of available packages and libraries
                  Platform: %s-%s
                  Sublime Text Version: %s
                  Package Control Version: %s
                ''',
                (
                    self.settings['platform'],
                    self.settings['arch'],
                    self.settings['version'],
                    __version__
                )
            )

        cache_ttl = self.settings.get('cache_length', 300)
        name_map = self.settings.get('package_name_map', {})
        downloaders = []
        executor = None
        providers = []
        packages = {}
        libraries = {}

        def download_repo(url):
            for provider_class in REPOSITORY_PROVIDERS:
                if provider_class.match_url(url):
                    provider = provider_class(url, self.settings)
                    provider.prefetch()
                    providers.append(provider)
                    break

        # Repositories are run in reverse order so that the ones first
        # on the list will overwrite those last on the list
        for repo in reversed(self.list_repositories()):
            if re.match(r'https?://([^.]+\.)*package-control\.io', repo):
                console_write('Removed malicious repository %s' % repo)
                continue

            if repo[:8].lower() == "file:///":
                repository_packages = None
                repository_libraries = None
            else:
                cache_key = repo + '.packages'
                repository_packages = get_cache(cache_key)
                if repository_packages:
                    packages.update(repository_packages)

                cache_key = repo + '.libraries'
                repository_libraries = get_cache(cache_key)
                if repository_libraries:
                    libraries.update(repository_libraries)

            if repository_packages is None and repository_libraries is None:
                if executor is None:
                    executor = futures.ThreadPoolExecutor(max_workers=10)
                downloaders.append(executor.submit(download_repo, repo))

        # wait for downloads to complete
        futures.wait(downloaders)

        # Grabs the results and stuff it all in the cache
        for provider in providers:
            repository_packages = {}
            unavailable_packages = []
            for name, info in provider.get_packages():
                name = name_map.get(name, name)
                info['name'] = name
                info['releases'] = self.select_releases(name, info['releases'])
                if info['releases']:
                    repository_packages[name] = info
                else:
                    unavailable_packages.append(name)

            repository_libraries = {}
            unavailable_libraries = []
            for name, info in provider.get_libraries():
                # Convert legacy dependency names to official pypi package names.
                # This is required for forward compatibility with upcomming changes
                # in scheme 4.0.0. Do it here to apply only on client side.
                name = info['name'] = library.translate_name(name)

                info['releases'] = self.select_releases(name, info['releases'])
                if info['releases']:
                    dist_name = library.escape_name(name).lower()
                    repository_libraries[dist_name] = info
                else:
                    unavailable_libraries.append(name)

            # Display errors we encountered while fetching package info
            for _, exception in provider.get_failed_sources():
                console_write(exception)
            for _, exception in provider.get_broken_packages():
                console_write(exception)
            for _, exception in provider.get_broken_libraries():
                console_write(exception)

            if provider.repo_url[:8].lower() != "file:///":
                cache_key = provider.repo_url + '.packages'
                set_cache(cache_key, repository_packages, cache_ttl)
                cache_key = provider.repo_url + '.libraries'
                set_cache(cache_key, repository_libraries, cache_ttl)

            packages.update(repository_packages)
            libraries.update(repository_libraries)

            renamed_packages = provider.get_renamed_packages()
            set_cache_under_settings(self, 'renamed_packages', provider.repo_url, renamed_packages, cache_ttl)

            set_cache_under_settings(
                self,
                'unavailable_packages',
                provider.repo_url,
                unavailable_packages,
                cache_ttl,
                list_=True
            )
            set_cache_under_settings(
                self,
                'unavailable_libraries',
                provider.repo_url,
                unavailable_libraries,
                cache_ttl,
                list_=True
            )

        self._available_packages = packages
        self._available_libraries = libraries

    def list_available_libraries(self):
        """
        Returns a master list of every available library from all sources that
        are compatible with the version of Python specified

        :return:
            A dict in the format:
            {
                'Library Name': {
                    # library details - see example-repository.json for format
                },
                ...
            }
        """

        if self._available_libraries is None:
            self.fetch_available()

        return self._available_libraries or {}

    def list_available_packages(self):
        """
        Returns a master list of every available package from all sources

        :return:
            A dict in the format:
            {
                'Package Name': {
                    # Package details - see example-repository.json for format
                },
                ...
            }
        """

        if self._available_packages is None:
            self.fetch_available()

        return self._available_packages or {}

    def list_libraries(self):
        """
        :return:
            A list of library.Library() objects for all installed libraries
        """

        return library.list_all()

    def list_packages(self, ignored_packages=None, unpacked_only=False, include_hidden=False):
        """
        List installed packages on the machine

        :param ignored_packages:
            A list of packages to ignore in returned result.
            The default value ``None`` or an empty list disables filtering.

        :param unpacked_only:
            Only list packages that are not inside of .sublime-package files

        :param include_hidden:
            If True, also return hidden packages

        :return:
            A set of all installed or overridden default package names
        """

        packages = set(list_sublime_package_dirs(sys_path.packages_path(), include_hidden))
        if unpacked_only is False:
            packages |= set(list_sublime_package_files(sys_path.installed_packages_path(), include_hidden))
        if ignored_packages:
            packages -= ignored_packages
        packages -= {'User'}
        return packages

    def list_default_packages(self):
        """
        Lists all built-in packages shipped with ST

        Packages can be packed as *.sublime-package or being extracted.

        :return:
            A set of default package names
        """

        default_packages_path = sys_path.default_packages_path()
        packages = set(list_sublime_package_dirs(default_packages_path, True))
        packages |= set(list_sublime_package_files(default_packages_path, True))
        packages -= {'User'}
        return packages

    def list_all_packages(self, include_hidden=False):
        """
        Lists all packages on the machine

        :param include_hidden:
            If True, also return hidden packages

        :return:
            A set of all package names, including default packages
        """

        return self.list_packages(include_hidden=include_hidden) | self.list_default_packages()

    def predefined_packages(self):
        """
        Return a set of predefined package names from registry.

        This method merges values of ``installed_packages`` settings from all
        Package Control.sublime-settings files found in any but the ``User`` package.

        It enables 3rd-party packages to ship predefined lists of packages to maintain
        available by Package Control via their own Package Control.sublime-settings.

        :returns:
            A set of ``installed_packages``.
        """

        merged = set()

        for file_name in sublime.find_resources('Package Control.sublime-settings'):
            if file_name.startswith('Packages/User/'):
                continue

            try:
                content = sublime.decode_value(sublime.load_resource(file_name))
                package_namess = content.get('installed_packages')
                if isinstance(package_namess, list):
                    merged |= set(package_namess)

            except (AttributeError, FileNotFoundError, ValueError) as e:
                console_write('Unable to load "%s": %s', (file_name, e))

        return merged

    def installed_packages(self):
        """
        Return a set of installed package names from registry.

        :returns:
            A set of ``installed_packages``.
        """

        with PackageManager.lock:
            settings = sublime.load_settings(pc_settings_filename())
            return (
                self.predefined_packages() |
                load_list_setting(settings, 'installed_packages')
            )

    def update_installed_packages(self, add=None, remove=None, persist=True):
        """
        Add and/or remove packages to installed package registry.

        :param add:
            A list/tuple/set of or a unicode string with the packages
            to add to the list of installed packages.

        :param remove:
            A list/tuple/set of or a unicode string with the packages
            to remove from the list of installed packages.

        :param persist:
            Save changed settings to disk.

        :returns:
            ``True`` if list of installed packages was updated
            ``False`` if list of installed packages was already up-to-date
        """

        with PackageManager.lock:
            file_name = pc_settings_filename()
            settings = sublime.load_settings(file_name)
            names_at_start = load_list_setting(settings, 'installed_packages')
            names = names_at_start.copy()

            if add:
                if isinstance(add, str):
                    add = {add}
                elif isinstance(add, (list, tuple)):
                    add = set(add)
                names |= add

            if remove:
                if isinstance(remove, str):
                    remove = {remove}
                elif isinstance(remove, (list, tuple)):
                    remove = set(remove)
                names -= remove

            names -= self.predefined_packages()

            result = names != names_at_start
            if result:
                settings.set('installed_packages', sorted(names, key=lambda s: s.lower()))
                if persist:
                    sublime.save_settings(file_name)

            return result

    def find_required_libraries(self):
        """
        Find all of the libraries required by the installed packages,
        ignoring the specified package.

        :return:
            A set of library.Library() objects for the libraries required by
            the installed packages
        """

        output = set()
        for package in self.list_packages(include_hidden=True):
            output |= self.get_libraries(package)

        output |= self.get_libraries('User')
        return output

    def find_missing_libraries(self, required_libraries=None):
        """
        Find missing libraries.

        :param required_libraries:
            All required libraries, for speed-up purposes.

        :return:
            A set of library.Library() objects for missing libraries
        """

        installed_libraries = self.list_libraries()
        if required_libraries is None:
            required_libraries = self.find_required_libraries()
        return required_libraries - installed_libraries

    def find_orphaned_libraries(self, required_libraries=None):
        """
        Find orphaned libraries.

        :param required_libraries:
            All required libraries, for speed-up purposes.

        :return:
            A set of library.Library() objects for no longer needed libraries
        """

        installed_libraries = self.list_libraries()
        if required_libraries is None:
            required_libraries = self.find_required_libraries()

        return set(lib for lib in installed_libraries - required_libraries if lib.is_managed())

    def _download_zip_file(self, name, url, sha256=None):
        try:
            content = http_get(url, self.settings, '')
            if sha256:
                content_hash = hashlib.sha256(content).hexdigest()
                if content_hash.lower() != sha256.lower():
                    console_write('Rejected download for "%s" due to checksum mismatch!', name)
                    return False

            return zipfile.ZipFile(BytesIO(content))

        except DownloaderException as e:
            console_write(
                '''
                Unable to download "%s": %s
                ''',
                (name, e)
            )
            return False

        except zipfile.BadZipfile:
            console_write(
                '''
                Failed to unzip the file for "%s"
                ''',
                name
            )
            return False

    def _common_folder(self, name, zf):
        """
        If all files in a zip file are contained in a single folder

        :param name:
            The name of the package or library

        :param zf:
            The zipfile instance

        :return:
            False if an error occurred, or a unicode string of the common
            folder name. If no common folder, a blank string is returned. If
            a folder name is returned, it will end in "/".
        """

        sep = '/'
        curdir = '.'
        unsafe = ('../', ':/', '..\\', ':\\')

        split_paths = []

        for info in zf.infolist():
            path = info.filename

            # Make sure there are no paths that look like security vulnerabilities
            if path[0] == '/' or any(p in path for p in unsafe):
                console_write(
                    '''
                    The archive for "%s" contains files that may traverse outside
                    of package root and cannot be safely installed, aborting
                    ''',
                    name
                )
                return False

            split_paths.append(path.split(sep))

        split_paths = [[c for c in s if c and c != curdir] for s in split_paths]
        s1 = min(split_paths)
        s2 = max(split_paths)
        common = s1
        for i, c in enumerate(s1):
            if c != s2[i]:
                common = s1[:i]
                break

        return sep.join(common) + sep if common else ''

    def _extract_zip(self, name, zf, src_dir, dest_dir, exclude=[], extracted_files=None):
        """
        Extracts a zip to a folder

        :param name:
            A unicode string of the package or library name

        :param zf:
            A zipfile instance to extract

        :param src_dir:
            A unicode string of the source directory to extract.
            If empty, all members are extracted.

        :param dest_dir:
            A unicode string of the destination directory

        :param exclude:
            Files not to extract.

        :param extracted_files:
            A set of all of the files paths extracted from the zip

        :return:
            A bool indication if the install should be retried
        """

        is_win = os.name == 'nt'

        # Here we don't use .extractall() since it was having issues on OS X
        for info in zf.infolist():
            source = info.filename

            if source.endswith('/'):
                continue

            if source in exclude:
                continue

            if is_win and any(c in source for c in ':*?"<>|'):
                console_write(
                    '''
                    Skipping file "%s" from archive for "%s" due to an invalid filename
                    ''',
                    (source, name)
                )
                continue

            # If there was only a single directory in the package, we remove
            # that folder name from the paths as we extract entries
            dest = sys_path.longpath(os.path.join(dest_dir, source[len(src_dir):]))
            parent = os.path.dirname(dest)
            os.makedirs(parent, exist_ok=True)

            try:
                with zf.open(info) as fsrc, open(dest, 'wb') as fdst:
                    shutil.copyfileobj(fsrc, fdst)

                # Restore executable permissions
                if (info.create_system == ZIP_UNIX_SYSTEM
                        and (info.external_attr >> 16) & S_IXUSR):
                    os.chmod(dest, os.stat(dest).st_mode | S_IXUSR)

            except OSError as e:
                if e.errno == 5 or e.errno == 13:  # permission denied
                    return True

                console_write(
                    '''
                    Skipping file "%s" from archive for "%s" due to IO error: %s
                    ''',
                    (source, name, e)
                )

            else:
                if extracted_files is not None:
                    extracted_files.add(os.path.normcase(dest))

        return False

    def install_libraries(self, libraries, fail_early=True):
        """
        Ensures a list of libraries are installed and up-to-date

        :param libraries:
            A list of library.Library() objects

        :param fail_early:
            Whether to abort installation if a library installation fails.

        :return:
            A boolean indicating if the libraries are properly installed
        """

        error = False
        for lib in sorted(libraries):
            if not self.install_library(lib):
                if fail_early:
                    return False
                error = True

        return not error

    def install_library(self, lib):
        """
        Install a library

        :param lib:
            The library.Library object to install

        :returns:
            True, if the library is successfully installed or upgraded
            False, if library could not be installed
        """

        debug = self.settings.get('debug')

        installed_version = None
        installed_library = library.find_installed(lib)
        if installed_library:
            installed_version = installed_library.dist_info.read_metadata().get('version')
            if installed_version:
                installed_version = pep440.PEP440Version(installed_version)

        is_upgrade = installed_library is not None
        if is_upgrade and not installed_library.is_managed():
            if debug:
                console_write(
                    'The library "%s" for Python %s was not installed by Package Control; leaving alone',
                    (lib.name, lib.python_version)
                )
            return True

        release = None
        available_version = None

        available_library = self.list_available_libraries().get(lib.dist_name)
        if available_library:
            for available_release in available_library['releases']:
                if lib.python_version in available_release['python_versions']:
                    # first found one is latest available
                    release = available_release
                    available_version = pep440.PEP440Version(release['version'])
                    break

        if available_version is None:
            is_unavailable = lib.name in self.settings.get('unavailable_libraries', [])
            if is_upgrade and is_unavailable:
                message = '''
                    The library "%s" is installed, but not available for Python %s
                    on this platform, or for this version of Sublime Text; leaving alone
                    '''
            elif is_upgrade:
                message = '''
                    The library "%s" is installed, but not available for Python %s; leaving alone
                    '''
            elif is_unavailable:
                message = '''
                    The library "%s" is not available for Python %s on this platform,
                    or this version of Sublime Text
                    '''
            else:
                message = 'The library "%s" is not available for Python %s'

            console_write(message, (lib.name, lib.python_version))
            return False

        if is_upgrade:
            if installed_version >= available_version:
                if debug:
                    console_write(
                        'The library "%s" for Python %s is installed and up to date',
                        (lib.name, lib.python_version)
                    )
                return True

            _, modified_ris = installed_library.dist_info.verify_files(missing_ok=True)
            modified_paths = {mri.absolute_path for mri in modified_ris}
            if modified_paths:
                console_write(
                    '''
                    Unable to upgrade library "%s" for Python %s because files on disk have been modified:
                      %s
                    ''',
                    (
                        lib.name,
                        lib.python_version,
                        '\n  '.join(sorted(map(sys_path.shortpath, modified_paths), key=lambda s: s.lower()))
                    )
                )
                return False

        lib_path = sys_path.lib_paths()[lib.python_version]
        tmp_dir = sys_path.longpath(tempfile.mkdtemp(''))
        tmp_library_dir = os.path.join(tmp_dir, lib.name)

        # This is refers to the zipfile later on, so we define it here so we can
        # close the zip file if set during the finally clause
        library_zip = None

        try:
            library_zip = self._download_zip_file(lib.name, release['url'], release.get("sha256"))
            if library_zip is False:
                return False

            common_folder = self._common_folder(lib.name, library_zip)
            if common_folder is False:
                return False

            should_retry = self._extract_zip(lib.name, library_zip, common_folder, tmp_library_dir)
            if should_retry:
                return False

            # search '<name>-<version>.dist-info/RECORD' directory in archive
            # be permissive with version part as it may have a different format as `available_version`
            new_did_name = None
            pattern = re.compile(r'({0.dist_name}-\S+\.dist-info)/RECORD'.format(lib), re.IGNORECASE)
            for i in library_zip.infolist():
                match = pattern.match(i.filename)
                if match:
                    new_did_name = match.group(1)
                    break

            if new_did_name:
                temp_did = library.distinfo.DistInfoDir(tmp_library_dir, new_did_name)
                _, modified_ris = temp_did.verify_files()
                modified_paths = {mri.absolute_path for mri in modified_ris}
                if modified_paths:
                    console_write(
                        '''
                        Unable to %s library "%s" for Python %s because files in the archive have been modified:
                          %s
                        ''',
                        (
                            'upgrade' if is_upgrade else 'install',
                            lib.name,
                            lib.python_version,
                            '\n  '.join(sorted(map(sys_path.shortpath, modified_paths), key=lambda s: s.lower()))
                        )
                    )
                    return False

                temp_did.write_installer()
                temp_did.add_installer_to_record()

                try:
                    temp_did.verify_python_version(lib.python_version)
                except EnvironmentError as e:
                    console_write(e)
                    return False

            else:
                try:
                    temp_did = library.convert_dependency(
                        tmp_library_dir,
                        lib.python_version,
                        lib.name,
                        available_version,
                        available_library.get('description'),
                        available_library.get('homepage')
                    )
                except ValueError as e:
                    console_write(
                        '''
                        Failed to install the library "%s" for Python %s: %s
                        ''',
                        (lib.name, lib.python_version, e)
                    )
                    return False

            if is_upgrade:
                try:
                    library.remove(installed_library)
                except OSError as e:
                    console_write(
                        '''
                        Failed to upgrade the library "%s" for Python %s: %s
                        ''',
                        (lib.name, lib.python_version, e)
                    )
                    return False

            library.install(temp_did, lib_path)

            if is_upgrade:
                console_write(
                    'Upgraded library "%s" from %s to %s for Python %s',
                    (lib.name, installed_version, available_version, lib.python_version))
            else:
                console_write(
                    'Installed library "%s" %s for Python %s',
                    (lib.name, available_version, lib.python_version))

            return True

        finally:
            # We need to make sure the zipfile is closed to
            # help prevent permissions errors on Windows
            if library_zip:
                library_zip.close()

            # Try to remove the tmp dir after a second to make sure
            # a virus scanner is holding a reference to the zipfile
            # after we close it.
            sublime.set_timeout(lambda: delete_directory(tmp_dir), 1000)

    def cleanup_libraries(self, required_libraries=None):
        """
        Remove all not needed libraries by the installed packages,
        ignoring the specified package.

        :param required_libraries:
            All required libraries, for speed-up purposes.

        :return:
            Boolean indicating the success of the removals.
        """

        orphaned_libraries = self.find_orphaned_libraries(required_libraries)

        error = False
        for lib in sorted(orphaned_libraries):
            if not self.remove_library(lib):
                error = True

        return not error

    def remove_library(self, lib):
        """
        Deletes a library

        :param lib:
            The library.InstalledLibrary() to delete

        :return:
            bool if the library was successfully deleted
        """

        try:
            library.remove(lib)

        except library.distinfo.DistInfoNotFoundError:
            console_write(
                '''
                The library specified, "%s" for Python %s, is not installed
                ''',
                (lib.name, lib.python_version)
            )
            return False

        except OSError:
            # THe way library.remove() works is that the .dist-info dir is
            # removed last. This means that any permissions errors will happen
            # before we remove the metadata, and thus we'll still think the
            # library is installed when ST restarts, and we can try removing
            # it again in the future.
            console_write(
                '''
                Failed to remove the library "%s" for Python %s -
                deferring until next start
                ''',
                (lib.name, lib.python_version)
            )
            return False

        else:
            console_write(
                '''
                Removed orphaned library "%s" for Python %s
                ''',
                (lib.name, lib.python_version)
            )
            return True

    def install_package(self, package_name, unattended=False):
        """
        Downloads and installs (or upgrades) a package

        Uses the self.list_available_packages() method to determine where to
        retrieve the package file from.

        The install process consists of:

        1. Finding the package
        2. Downloading the .sublime-package/.zip file
        3. Extracting the package file
        4. Showing install/upgrade messaging
        5. Submitting usage info
        6. Recording that the package is installed

        :param package_name:
            The package to download and install

        :param unattended:
            If ``True`` suppress message dialogs and don't focus "Package Control Messages".

        :return: bool if the package was successfully installed or None
                 if the package needs to be cleaned up on the next restart
                 and should not be re-enabled
        """

        # Handle VCS packages first as those might not be registered
        # in one of the repositories or channels.
        upgrader = self.instantiate_upgrader(package_name)
        if upgrader:
            # We explicitly don't support the "libraries" key when dealing
            # with packages installed via VCS
            to_ignore = self.settings.get('ignore_vcs_packages')
            if to_ignore is True:
                console_write(
                    '''
                    Skipping %s package "%s" since the setting
                    "ignore_vcs_packages" is set to true
                    ''',
                    (upgrader.cli_name, package_name)
                )
                return False

            if isinstance(to_ignore, list) and package_name in to_ignore:
                console_write(
                    '''
                    Skipping %s package "%s" since it is listed in the
                    "ignore_vcs_packages" setting
                    ''',
                    (upgrader.cli_name, package_name)
                )
                return False

            result = upgrader.run()

            # We are done here, if the package is an unmanaged VCS package.
            # Otherwise the package might just be an override.
            if not zip_file_exists(package_name, 'package-metadata.json'):
                console_write('Upgraded %s', package_name)
                return result

        # package is to be renamed during upgrade
        old_package_name = package_name
        package_name = self.settings.get('renamed_packages', {}).get(package_name) or package_name

        packages = self.list_available_packages()
        if package_name not in packages:
            if package_name in self.settings.get('unavailable_packages', []):
                console_write(
                    '''
                    The package "%s" is either not available on this platform or for
                    this version of Sublime Text
                    ''',
                    package_name
                )
            else:
                console_write('The package "%s" is not available', package_name)

            return False

        package = packages[package_name]
        release = package['releases'][0]

        package_dir = get_package_dir(package_name)
        package_file = get_installed_package_path(package_name)
        package_filename = os.path.basename(package_file)

        tmp_dir = sys_path.longpath(tempfile.mkdtemp(''))
        tmp_package_file = os.path.join(tmp_dir, package_filename)

        # This is refers to the zipfile later on, so we define it here so we can
        # close the zip file if set during the finally clause
        package_zip = None

        try:
            old_metadata = self.get_metadata(old_package_name)
            old_version = old_metadata.get('version')
            is_upgrade = old_version is not None

            package_zip = self._download_zip_file(package_name, release['url'], release.get("sha256"))
            if package_zip is False:
                return False

            common_folder = self._common_folder(package_name, package_zip)
            if common_folder is False:
                return False

            # By default, ST prefers .sublime-package files since this allows
            # overriding files in the Packages/{package_name}/ folder.
            #
            # Exceptions:
            # 1. `Packages/Default` must not be overridden completely,
            #    to prevent core functionality breaking.
            # 2. Package maintainer wants it being installed as unpacked folder
            #    by adding a .no-sublime-package ile
            unpack = package_name.lower() == 'default'
            if not unpack:
                try:
                    package_zip.getinfo(common_folder + '.no-sublime-package')
                    unpack = True
                except (KeyError):
                    unpack = False

            supported_python_versions = sys_path.python_versions()
            python_version = "3.3"

            try:
                python_version_file = common_folder + '.python-version'
                python_version_raw = package_zip.read(python_version_file).decode('utf-8').strip()
                if python_version_raw in supported_python_versions:
                    python_version = python_version_raw
            except (KeyError):
                # no .python-version found in archive,
                # get best matching python version from upstream release data
                python_versions = release.get("python_versions")
                if python_versions:
                    python_version_raw = str(
                        max(map(pep440.PEP440Version, set(python_versions) & supported_python_versions))
                    )
                    if python_version_raw:
                        python_version = python_version_raw

            original_python_version = python_version

            # Try to read .python-version from existing unpacked package directory to respect local
            # opt-in to certain plugin_host and to install correct libraries.
            try:
                python_version_file = os.path.join(get_package_dir(old_package_name), '.python-version')
                with open(python_version_file, 'r', encoding='utf-8') as fobj:
                    python_version_raw = fobj.read().strip()
                    if python_version_raw in supported_python_versions and (
                        unpack or pep440.PEP440Version(python_version_raw) > pep440.PEP440Version(python_version)
                    ):
                        python_version = python_version_raw
            except (FileNotFoundError):
                pass

            if package_name != old_package_name:
                self.rename_package(old_package_name, package_name)

            # If we determined it should be unpacked, we extract directly
            # into the Packages/{package_name}/ folder
            if unpack:
                # Make sure not to overwrite existing hidden packages or package overrides
                #
                # A hidden unpacked package is expected to have been created locally,
                # either manually by user or dynamically by a plugin.
                #
                # It may serve as:
                # a) override for a *.sublime-package file.
                # b) invisible helper package, which can't be enabled/disabled/removed
                #    by user via API/GUI (if no corresponding *.sublime-package file exists)
                if regular_file_exists(package_name, '.hidden-sublime-package'):
                    console_write(
                        '''
                        Failed to %s %s -
                        Overwriting existing hidden package not allowed.
                        ''',
                        ('upgrade' if is_upgrade else 'install', package_name)
                    )
                    return False

                if not self.backup_package_dir(package_name):
                    return False

            # Otherwise we go into a temp dir since we will be creating a
            # new .sublime-package file later
            else:
                # If we already have a package-metadata.json file in
                # Packages/{package_name}/, but the package no longer contains
                # a .no-sublime-package file, then we want to clear the unpacked
                # dir and install as a .sublime-package file. Since we are only
                # clearing if a package-metadata.json file exists, we should never
                # accidentally delete user's customizations. However, we still
                # create a backup just in case.
                if regular_file_exists(package_name, 'package-metadata.json'):
                    if not self.backup_package_dir(package_name):
                        return False

                    if not delete_directory(package_dir):
                        # If deleting failed, queue the package to upgrade upon next start
                        # when it will be disabled
                        reinstall_file = os.path.join(package_dir, 'package-control.reinstall')
                        create_empty_file(reinstall_file)
                        console_write(
                            '''
                            Failed to upgrade %s -
                            deferring until next start
                            ''',
                            package_name
                        )
                        return None

                package_dir = os.path.join(tmp_dir, 'working')

            package_metadata_file = os.path.join(package_dir, 'package-metadata.json')

            extracted_files = set()
            should_retry = self._extract_zip(
                package_name,
                package_zip,
                common_folder,
                package_dir,
                [common_folder + "__init__.py"],
                extracted_files,
            )

            package_zip.close()
            package_zip = None

            # If upgrading failed, queue the package to upgrade upon next start
            if should_retry:
                if unpack:
                    reinstall_file = os.path.join(package_dir, 'package-control.reinstall')
                    create_empty_file(reinstall_file)

                    # Don't delete the metadata file, that way we have it
                    # when the reinstall happens, and the appropriate
                    # usage info can be sent back to the server.
                    # No need to handle symlink at this stage it was already removed
                    # and we are not working with symlink here any more.
                    clear_directory(package_dir, {reinstall_file, package_metadata_file})

                console_write(
                    '''
                    Failed to upgrade %s -
                    deferring until next start
                    ''',
                    package_name
                )
                return None

            # Here we clean out any files that were not just overwritten. It is ok,
            # if there is an error removing a file. The next time there is an
            # upgrade, it should be cleaned out successfully then.
            # No need to handle symlink at this stage it was already removed
            # and we are not working with symlink here any more.
            if unpack:
                clear_directory(package_dir, extracted_files)

            # Create .python-version file to opt-in to certain plugin_host.
            # It enables unmaintained packages/plugins to be opted-in to newer python version
            # via upstream release information or via local settings.
            if python_version != '3.3':
                try:
                    python_version_file = os.path.join(package_dir, '.python-version')
                    with open(python_version_file, 'x') as fobj:
                        fobj.write(python_version)
                except FileExistsError:
                    pass

            new_version = release['version']

            self.print_messages(package_name, package_dir, is_upgrade, old_version, new_version, unattended)

            with open(package_metadata_file, 'w', encoding='utf-8') as fobj:
                now = time.time()
                install_time = old_metadata.get("install_time", now)
                metadata = {
                    "name": package_name,
                    "version": new_version,
                    "sublime_text": release['sublime_text'],
                    "platforms": release['platforms'],
                    "python_version": original_python_version,
                    "url": package['homepage'],
                    "issues": package['issues'],
                    "author": package['author'],
                    "description": package['description'],
                    "labels": package['labels'],
                    "libraries": release.get('libraries', []),
                    "install_time": install_time,
                    "release_time": release['date'],
                }
                if is_upgrade:
                    metadata['upgrade_time'] = now
                json.dump(metadata, fobj)

            # Submit install and upgrade info
            if is_upgrade:
                params = {
                    'package': package_name,
                    'operation': 'upgrade',
                    'version': new_version,
                    'old_version': old_version
                }
            else:
                params = {
                    'package': package_name,
                    'operation': 'install',
                    'version': new_version
                }
            self.record_usage(params)

            # Record the install in the settings file so that you can move
            # settings across computers and have the same packages installed
            self.update_installed_packages(
                add=package_name,
                remove=old_package_name if package_name != old_package_name else None,
                persist=False
            )

            # If we extracted directly into the Packages/{package_name}/
            # we probably need to remove an old Installed Packages/{package_name].sublime-package
            if unpack:
                try:
                    os.remove(package_file)
                except (FileNotFoundError):
                    pass
                except (OSError) as e:
                    console_write(
                        '''
                        Unable to remove "%s" after upgrade to unpacked package: %s
                        ''',
                        (package_filename, e)
                    )

            # If we didn't extract directly into the Packages/{package_name}/
            # folder, we need to create a .sublime-package file and install it
            else:
                try:
                    with zipfile.ZipFile(tmp_package_file, "w", compression=zipfile.ZIP_DEFLATED) as fobj:
                        for root, _, files in os.walk(package_dir):
                            for file in files:
                                full_path = os.path.join(root, file)
                                relative_path = os.path.relpath(full_path, package_dir)
                                fobj.write(full_path, relative_path)

                except (OSError, IOError) as e:
                    console_write(
                        '''
                        Failed to create the package file "%s" in %s: %s
                        ''',
                        (package_filename, tmp_dir, e)
                    )
                    return False

                try:
                    try:
                        os.remove(package_file)
                    except (FileNotFoundError):
                        pass
                    shutil.move(tmp_package_file, package_file)

                except (OSError):
                    try:
                        shutil.move(tmp_package_file, package_file + '-new')
                    except (OSError):
                        pass

                    console_write(
                        '''
                        Failed to upgrade %s -
                        deferring until next start
                        ''',
                        package_name
                    )
                    return None

            if is_upgrade:
                console_write(
                    'Upgraded package "%s" from %s to %s',
                    (package_name, old_version, new_version)
                )
            else:
                console_write(
                    'Installed package "%s" %s',
                    (package_name, new_version)
                )

            return True

        finally:
            # We need to make sure the zipfile is closed to
            # help prevent permissions errors on Windows
            if package_zip:
                package_zip.close()

            # Try to remove the tmp dir after a second to make sure
            # a virus scanner is holding a reference to the zipfile
            # after we close it.
            sublime.set_timeout_async(lambda: delete_directory(tmp_dir), 1000)

    def rename_package(self, package_name, new_package_name):
        """
        Rename a package

        :param package_name:
            The package name
        :param new_package_name:
            The new package name

        :returns:
            ``True`` on success
            ``False`` if package can not be renamed
        """

        # User package needs to be checked as it exists in Data/Packages/
        if package_name.lower() == 'user' or new_package_name.lower() == 'user':
            console_write(
                '''
                The package "%s" can not be renamed
                ''',
                package_name
            )
            return False

        case_insensitive_fs = self.settings['platform'] in ['windows', 'osx']
        changing_case = case_insensitive_fs and package_name.lower() == new_package_name.lower()

        def do_rename(old, new):
            # Windows will not allow you to rename to the same name with
            # a different case, so we work around that with a temporary name
            if changing_case:
                temp_path = os.path.join(os.path.dirname(sublime.packages_path()), new + "-renaming")
                os.rename(old, temp_path)
                old = temp_path

            os.rename(old, new)

        package_file = get_installed_package_path(package_name)

        try:
            do_rename(package_file, get_installed_package_path(new_package_name))
        except FileNotFoundError:
            # package file does not exist, nothing to do
            pass
        except FileExistsError:
            # delete source file if destination already exists
            try:
                os.remove(package_file)
            except (OSError, IOError) as e:
                if self.settings.get('debug'):
                    console_write(
                        '''
                        Unable to remove package "%s" -
                        deferring until next start: %s
                        ''',
                        (package_name, e)
                    )

        package_dir = get_package_dir(package_name)

        try:
            do_rename(package_dir, get_package_dir(new_package_name))
        except FileNotFoundError:
            # package dir does not exist, nothing to do
            pass
        except FileExistsError:
            # delete source dir if destination already exists
            if not self.backup_package_dir(package_name):
                console_write('It is therefore not removed automatically.')

            elif not delete_directory(package_dir):
                if self.settings.get('debug'):
                    console_write(
                        '''
                        Unable to remove directory for package "%s" -
                        deferring until next start
                        ''',
                        package_name
                    )
                create_empty_file(os.path.join(package_dir, 'package-control.cleanup'))

        # Remove optionally present cache if exists
        # ST will recreate cache for renamed packages, automatically
        delete_directory(get_package_cache_dir(package_name))
        delete_directory(get_package_module_cache_dir(package_name))

        return True

    def remove_package(self, package_name):
        """
        Deletes a package

        The deletion process consists of:

        1. Removing the package from the list of installed packages
        2. Deleting the directory (or marking it for deletion if deletion fails)
        3. Submitting usage info

        :param package_name:
            The package to delete

        :return:
            ``True`` if the package was successfully deleted
            ``False`` if the package doesn't exist or can not be deleted
            ``None`` if the package needs to be cleaned up on the next restart
            and should not be re-enabled
        """

        self.update_installed_packages(remove=package_name, persist=False)

        version = self.get_metadata(package_name).get('version')

        result = self.delete_package(package_name)
        if result is not False:
            self.record_usage({
                'package': package_name,
                'operation': 'remove',
                'version': version
            })

            # Remove libraries that are no longer needed
            self.cleanup_libraries()

        return result

    def delete_package(self, package_name):
        """
        Delete package resources from filesystem.

        The method removes all package related files and directories without
        manipulating any metadata such as installed_packages or uploading usage data.

        :param package_name:
            The package to delete

        :return:
            ``True`` if the package was successfully deleted
            ``False`` if the package doesn't exist or can not be deleted
            ``None`` if the package needs to be cleaned up on the next restart
            and should not be re-enabled
        """

        # User package needs to be checked as it exists in Data/Packages/
        if package_name.lower() == 'user':
            console_write(
                '''
                The package "%s" can not be removed
                ''',
                package_name
            )
            return False

        package_file = get_installed_package_path(package_name)
        package_dir = get_package_dir(package_name)

        can_delete_file = os.path.exists(package_file)
        can_delete_dir = os.path.exists(package_dir)

        if not can_delete_file and not can_delete_dir:
            console_write(
                '''
                The package "%s" is not installed
                ''',
                package_name
            )
            return False

        result = True

        if can_delete_file:
            try:
                os.remove(package_file)
            except OSError:
                try:
                    trash_path = sys_path.trash_path()
                    os.makedirs(trash_path, exist_ok=True)
                    # Try to move file to "Trash" directory.
                    # Required for e.g. Sublime Merge to unload the package and unlock the file.
                    # Note: Locked files on Windows OS can still be renamed.
                    trash_path = os.path.join(
                        trash_path,
                        hashlib.sha1(
                            (str(self.session_time) + package_file).encode('utf-8')
                        ).hexdigest().lower()
                    )
                    os.rename(package_file, trash_path)
                except OSError as e:
                    if self.settings.get('debug'):
                        console_write(
                            '''
                            Unable to remove package "%s" -
                            deferring until next start: %s
                            ''',
                            (package_name, e)
                        )
                    result = None

        if can_delete_dir:
            if not self.backup_package_dir(package_name):
                console_write('It is therefore not removed automatically.')

            elif not delete_directory(package_dir):
                if self.settings.get('debug'):
                    console_write(
                        '''
                        Unable to remove directory for package "%s" -
                        deferring until next start
                        ''',
                        package_name
                    )
                create_empty_file(os.path.join(package_dir, 'package-control.cleanup'))
                result = None

        # remove optionally present cache if exists
        delete_directory(get_package_cache_dir(package_name))
        delete_directory(get_package_module_cache_dir(package_name))

        message = 'Removed package "%s"' % package_name
        if result is None:
            message += ' and scheduled clean up on next restart'
        console_write(message)

        return result

    def backup_package_dir(self, package_name):
        """
        Does a full backup of the Packages/{package}/ dir to Backup/

        :param package_name:
            The name of the package to back up

        :return:
            If the backup succeeded
        """

        package_dir = get_package_dir(package_name)
        if not os.path.exists(package_dir):
            return True

        backup_dir = os.path.join(
            sys_path.data_path(), 'Backup', self.session_time.strftime('%Y%m%d%H%M%S')
        )
        package_backup_dir = os.path.join(backup_dir, package_name)

        try:
            if os.path.exists(package_backup_dir):
                console_write(
                    '''
                    Backup folder "%s" already exists!
                    ''',
                    package_backup_dir
                )
            else:
                os.makedirs(backup_dir, exist_ok=True)
            shutil.copytree(package_dir, package_backup_dir)
            return True

        except (OSError, IOError) as e:
            delete_directory(package_backup_dir)
            console_write(
                '''
                Failed to backup the package directory for "%s": %s
                ''',
                (package_name, e)
            )
            return False

    def prune_backup_dir(self):
        """
        Remove all backups older than ``max_backup_age`` days.
        """

        age = max(0, self.settings.get('max_backup_age', 14))
        today = datetime.date.today()
        backup_dir = os.path.join(sys_path.data_path(), 'Backup')

        if not os.path.isdir(backup_dir):
            return

        for fname in os.listdir(backup_dir):
            package_backup_dir = os.path.join(backup_dir, fname)
            if not os.path.isdir(package_backup_dir):
                continue

            try:
                date = datetime.date(int(fname[:4]), int(fname[4:6]), int(fname[6:8]))
                if (today - date).days > age:
                    delete_directory(package_backup_dir)
            except ValueError:
                continue

    def print_messages(self, package_name, package_dir, is_upgrade, old_version, new_version, unattended):
        """
        Prints out package install and upgrade messages

        The functionality provided by this allows package maintainers to
        show messages to the user when a package is installed, or when
        certain version upgrade occur.

        :param package_name:
            The name of the package the message is for

        :param package_dir:
            The full filesystem path to the package directory

        :param is_upgrade:
            If the install was actually an upgrade

        :param old_version:
            The string version of the package before the upgrade occurred

        :param new_version:
            The new (string) version of the package

        :param unattended:
            If ``True`` don't focus "Package Control Messages".
        """

        if self.settings["print_messages"] == "disabled":
            return
        elif self.settings["print_messages"] == "background":
            unattended = True
        elif self.settings["print_messages"] == "foreground":
            unattended = False

        try:
            messages_file = os.path.join(package_dir, 'messages.json')
            with open(messages_file, 'r', encoding='utf-8') as fobj:
                message_info = json.load(fobj)
        except (FileNotFoundError):
            return
        except (ValueError):
            console_write(
                '''
                Error parsing messages.json for %s
                ''',
                package_name
            )
            return

        def read_message(message_path):
            with open(sys_path.longpath(message_path), 'r', encoding='utf-8', errors='replace') as fobj:
                return '\n  %s\n' % fobj.read().rstrip().replace('\n', '\n  ')

        output = ''
        if not is_upgrade:
            install_file = message_info.get('install')
            if install_file:
                try:
                    install_path = os.path.join(package_dir, install_file)
                    output += read_message(install_path)
                except (FileNotFoundError):
                    console_write(
                        '''
                        Error opening install message for %s from %s
                        ''',
                        (package_name, install_file)
                    )

        elif is_upgrade and old_version:
            old_version_cmp = PackageVersion(old_version)
            new_version_cmp = PackageVersion(new_version)

            for version in version_sort(set(message_info) - {'install'}, reverse=True):
                version_cmp = PackageVersion(version)
                if version_cmp <= old_version_cmp:
                    break
                # If the package developer sets up release notes for future
                # versions, we don't want to show them for every release
                if version_cmp > new_version_cmp:
                    continue

                upgrade_file = message_info.get(version)
                upgrade_path = os.path.join(package_dir, upgrade_file)

                try:
                    output += read_message(upgrade_path)
                except (FileNotFoundError):
                    console_write(
                        '''
                        Error opening %s message for %s from %s
                        ''',
                        (version, package_name, upgrade_file)
                    )

        if not output:
            return

        def print_message(package_name, output, unattended):
            """
            Prints a message in UI thread

            By running in UI thread, the active view keeps focused, when optionally creating
            or updating the Package Control Messages output view in background.

            :param package_name:
                The package name to print update message for.

            :param output:
                string to print

            :param unattended:
                If `True` the message view is created in background without stealing focus
                of active view.
            """
            output = "\n\n{}\n{}\n{}".format(package_name, '-' * len(package_name), output)

            window = None
            view = None
            view_name = 'Package Control Messages'

            for _window in sublime.windows():
                for _view in _window.views():
                    if _view.name() == view_name:
                        window = _window
                        view = _view
                        break

            if view is None:
                window = sublime.active_window()
                if not window:
                    window = sublime.windows()[0]

                active_view = window.active_view()

                view = window.new_file()
                window.set_view_index(view, 0, 0)

                if unattended and active_view:
                    window.focus_view(active_view)

                view.set_name(view_name)
                view.set_scratch(True)
                settings = view.settings()
                settings.set('auto_complete', False)
                settings.set('auto_indent', False)
                settings.set('gutter', False)
                settings.set('tab_width', 2)
                settings.set('word_wrap', True)

            # As 'package_control_message' command is not available during
            # Package Control upgrade, fallback to built-in commands to insert message
            if package_name == 'Package Control':
                output = "{}\n{}\n{}".format(view_name, '=' * len(view_name), output)
                view.run_command('move_to', {'to': 'eof'})
                view.run_command('move_to', {'to': 'bof', 'extend': True})
                view.set_read_only(False)
                view.run_command('insert', {'characters': output})
                view.set_read_only(True)
                view.run_command('move_to', {'to': 'bof'})
                return

            # append message to view without touching scroll position or selection
            view.run_command('package_control_message', {'message': output})

        sublime.set_timeout(partial(print_message, package_name, output, unattended))

    def record_usage(self, params):
        """
        Submits install, upgrade and delete actions to a usage server

        The usage information is currently displayed on the Package Control
        website at https://packagecontrol.io

        :param params:
            A dict of the information to submit
        """

        if not self.settings.get('submit_usage'):
            return

        params['package_control_version'] = self.get_metadata('Package Control').get('version')
        params['sublime_platform'] = self.settings.get('platform')
        params['sublime_version'] = self.settings.get('version')

        # packagecontrol.io
        url = self.settings.get('submit_url', '')
        if url:
            url += '?' + urlencode(params)

            try:
                result = http_get(url, self.settings, 'Error submitting usage information.')
            except (DownloaderException) as e:
                console_write(e)
                return

            try:
                result = json.loads(result.decode('utf-8'))
                if result['result'] != 'success':
                    raise ValueError()
            except (ValueError):
                console_write(
                    '''
                    Error submitting usage information for %s
                    ''',
                    params['package']
                )

        # stats.sublimetext.io
        url = self.settings.get('submit_usage_url', '')
        if url:
            # rename some parameters
            params["pkg"] = params["package"]
            del params["package"]
            params["type"] = params["operation"]
            del params["operation"]
            # create url
            url += '?' + urlencode(params)

            try:
                result = http_get(url, self.settings, 'Error submitting usage information.')
            except (DownloaderException) as e:
                console_write(e)
                return

            if result.strip() != b'OK':
                console_write(
                    '''
                    Error submitting usage information for %s
                    ''',
                    params['pkg']
                )
