import os
import re
import json
import zipfile
import shutil
from fnmatch import fnmatch
import datetime
import tempfile
# To prevent import errors in thread with datetime
import locale  # noqa
from urllib.parse import urlencode, urlparse
import compileall


import sublime

from .show_error import show_error
from .console_write import console_write
from .clear_directory import clear_directory, unlink_or_delete_directory, is_directory_symlink
from .cache import clear_cache, set_cache, get_cache, merge_cache_under_settings, set_cache_under_settings
from .versions import version_comparable, version_sort
from .downloaders.background_downloader import BackgroundDownloader
from .downloaders.downloader_exception import DownloaderException
from .providers.provider_exception import ProviderException
from .clients.client_exception import ClientException
from .download_manager import downloader
from .providers.release_selector import filter_releases, is_compatible_version
from .upgraders.git_upgrader import GitUpgrader
from .upgraders.hg_upgrader import HgUpgrader
from .package_io import read_package_file
from .providers import CHANNEL_PROVIDERS, REPOSITORY_PROVIDERS
from .settings import pc_settings_filename, load_list_setting, save_list_setting
from . import distinfo, library, sys_path, text
from . import __version__


DEFAULT_CHANNEL = 'https://packagecontrol.io/channel_v3.json'
OLD_DEFAULT_CHANNELS = set([
    'https://packagecontrol.io/channel.json',
    'https://sublime.wbond.net/channel.json',
    'https://sublime.wbond.net/repositories.json'
])


class PackageManager():

    """
    Allows downloading, creating, installing, upgrading, and deleting packages

    Delegates metadata retrieval to the CHANNEL_PROVIDERS classes.
    Uses VcsUpgrader-based classes for handling git and hg repositories in the
    Packages folder. Downloader classes are utilized to fetch contents of URLs.

    Also handles displaying package messaging, and sending usage information to
    the usage server.
    """

    def __init__(self):
        # Here we manually copy the settings since sublime doesn't like
        # code accessing settings from threads
        self.settings = {}
        settings = sublime.load_settings(pc_settings_filename())
        setting_names = [
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
            'http_cache',
            'http_cache_length',
            'http_proxy',
            'https_proxy',
            'ignore_vcs_packages',
            'install_prereleases',
            'package_destination',
            'package_name_map',
            'package_profiles',
            'proxy_password',
            'proxy_username',
            'renamed_packages',
            'repositories',
            'submit_url',
            'submit_usage',
            'timeout',
            'user_agent'
        ]
        for setting in setting_names:
            if settings.get(setting) is None:
                continue
            self.settings[setting] = settings.get(setting)

        # https_proxy will inherit from http_proxy unless it is set to a
        # string value or false
        no_https_proxy = self.settings.get('https_proxy') in ["", None]
        if no_https_proxy and self.settings.get('http_proxy'):
            self.settings['https_proxy'] = self.settings.get('http_proxy')
        if self.settings.get('https_proxy') is False:
            self.settings['https_proxy'] = ''

        # We cache these to prevent IPC calls between plugin_host and the main
        # Sublime Text executable
        self.settings['platform'] = sublime.platform()
        self.settings['arch'] = sublime.arch()
        self.settings['version'] = int(sublime.version())

        # Use the cache to see if settings have changed since the last
        # time the package manager was created, and clearing any cached
        # values if they have.
        previous_settings = get_cache('filtered_settings', {})

        # Reduce the settings down to exclude channel info since that will
        # make the settings always different
        filtered_settings = self.settings.copy()
        for key in ['repositories', 'channels', 'package_name_map', 'cache']:
            if key in filtered_settings:
                del filtered_settings[key]

        if filtered_settings != previous_settings and previous_settings != {}:
            console_write(
                '''
                Settings change detected, clearing cache
                '''
            )
            clear_cache()
        set_cache('filtered_settings', filtered_settings)

    def get_python_version(self, package_name):
        """
        Returns the version of python a package runs under

        :param package_name:
            The name of the package

        :return:
            A unicode string of "3.3" or "3.8"
        """

        python_version = read_package_file(package_name, ".python-version")
        if python_version and python_version.strip() == "3.8":
            return "3.8"

        return "3.3"

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

        metadata_filename = 'package-metadata.json'
        metadata_json = read_package_file(package_name, metadata_filename)
        if metadata_json:
            try:
                return json.loads(metadata_json)
            except (ValueError):
                console_write(
                    '''
                    An error occurred while trying to parse the package
                    metadata for %s.
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
            A list of library.Library() objects
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
                    An error occurred while trying to parse the
                    dependencies.json for %s.
                    ''',
                    package_name
                )

        if names is None:
            metadata = self.get_metadata(package_name)
            # "dependencies" key is for backwards compatibility
            names = metadata.get('libraries', metadata.get('dependencies', []))

        if not names:
            return set()

        return set(library.Library(name, python_version) for name in names)

    def _is_git_package(self, package_name):
        """
        :param package_name:
            The package name

        :return:
            If the package is installed via git
        """

        git_dir = os.path.join(self.get_package_dir(package_name), '.git')
        return os.path.isdir(git_dir) or os.path.isfile(git_dir)

    def _is_hg_package(self, package_name):
        """
        :param package_name:
            The package name

        :return:
            If the package is installed via hg
        """

        hg_dir = os.path.join(self.get_package_dir(package_name), '.hg')
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

    def get_version(self, package_name):
        """
        Determines the current version for a package

        :param package_name:
            The package name
        """

        version = self.get_metadata(package_name).get('version')

        if version:
            return version

        if self.is_vcs_package(package_name):
            upgrader = self.instantiate_upgrader(package_name)
            version = upgrader.latest_commit()
            if version:
                return '%s commit %s' % (upgrader.cli_name, version)

        return 'unknown version'

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
                self.get_package_dir(package_name),
                self.settings['cache_length'],
                self.settings['debug']
            )

        if self._is_hg_package(package_name):
            return HgUpgrader(
                self.settings['hg_binary'],
                self.settings['hg_update_command'],
                self.get_package_dir(package_name),
                self.settings['cache_length'],
                self.settings['debug']
            )

        return None

    def select_libraries(self, library_info):
        """
        Takes the a dict from a dependencies.json file and returns the
        library names that are applicable to the current machine

        :param library_info:
            A dict from a dependencies.json file

        :return:
            A list of library names
        """

        platform_selectors = [
            self.settings['platform'] + '-' + self.settings['arch'],
            self.settings['platform'],
            '*'
        ]

        st_version = self.settings['version']

        for platform_selector in platform_selectors:
            if platform_selector not in library_info:
                continue

            platform_library = library_info[platform_selector]
            versions = platform_library.keys()

            # Sorting reverse will give us >, < then *
            for version_selector in sorted(versions, reverse=True):
                if not is_compatible_version(version_selector, st_version):
                    continue
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

        cache_ttl = self.settings.get('cache_length')

        repositories = self.settings.get('repositories')[:]
        channels = self.settings.get('channels')

        # Update any old default channel URLs users have in their config
        updated_channels = []
        found_default = False
        for channel in channels:
            if re.match(r'https?://([^.]+\.)*package-control\.io', channel):
                console_write('Removed malicious channel %s' % channel)
                continue
            if channel in OLD_DEFAULT_CHANNELS:
                if not found_default:
                    updated_channels.append(DEFAULT_CHANNEL)
                    found_default = True
                continue
            updated_channels.append(channel)

        for channel in updated_channels:
            channel = channel.strip()

            # Caches various info from channels for performance
            cache_key = channel + '.repositories'
            channel_repositories = get_cache(cache_key)

            merge_cache_under_settings(self, 'package_name_map', channel)
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

                try:
                    channel_repositories = provider.get_repositories()
                    set_cache(cache_key, channel_repositories, cache_ttl)

                    unavailable_packages = []
                    unavailable_libraries = []

                    for repo in channel_repositories:
                        original_packages = provider.get_packages(repo)
                        filtered_packages = {}
                        for package in original_packages:
                            info = original_packages[package]
                            info['releases'] = filter_releases(package, self.settings, info['releases'])
                            if info['releases']:
                                filtered_packages[package] = info
                            else:
                                unavailable_packages.append(package)
                        packages_cache_key = repo + '.packages'
                        set_cache(packages_cache_key, filtered_packages, cache_ttl)

                        original_libraries = provider.get_libraries(repo)
                        filtered_libraries = {}
                        for lib_name in original_libraries:
                            info = original_libraries[lib_name]
                            info['releases'] = filter_releases(lib_name, self.settings, info['releases'])
                            if info['releases']:
                                filtered_libraries[lib_name] = info
                            else:
                                unavailable_libraries.append(lib_name)
                        libraries_cache_key = repo + '.libraries'
                        set_cache(libraries_cache_key, filtered_libraries, cache_ttl)

                    # Have the local name map override the one from the channel
                    name_map = provider.get_name_map()
                    set_cache_under_settings(self, 'package_name_map', channel, name_map, cache_ttl)

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

    def _list_available(self):
        """
        Returns a master list of every available package and library from all sources

        :return:
            A 2-element tuple, in the format:
            (
                {
                    'Package Name': {
                        # Package details - see example-repository.json for format
                    },
                    ...
                },
                {
                    'Library Name': {
                        # Library details - see example-repository.json for format
                    },
                    ...
                }
            )
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

        cache_ttl = self.settings.get('cache_length')
        repositories = self.list_repositories()
        packages = {}
        libraries = {}
        bg_downloaders = {}
        active = []
        repos_to_download = []
        name_map = self.settings.get('package_name_map', {})

        # Repositories are run in reverse order so that the ones first
        # on the list will overwrite those last on the list
        for repo in repositories[::-1]:
            if re.match(r'https?://([^.]+\.)*package-control\.io', repo):
                console_write('Removed malicious repository %s' % repo)
                continue

            cache_key = repo + '.packages'
            repository_packages = get_cache(cache_key)

            if repository_packages is not None:
                packages.update(repository_packages)

                cache_key = repo + '.libraries'
                repository_libraries = get_cache(cache_key)
                libraries.update(repository_libraries)

            else:
                domain = urlparse(repo).hostname
                if domain not in bg_downloaders:
                    bg_downloaders[domain] = BackgroundDownloader(
                        self.settings, REPOSITORY_PROVIDERS)
                bg_downloaders[domain].add_url(repo)
                repos_to_download.append(repo)

        for bg_downloader in list(bg_downloaders.values()):
            bg_downloader.start()
            active.append(bg_downloader)

        # Wait for all of the downloaders to finish
        while active:
            bg_downloader = active.pop()
            bg_downloader.join()

        # Grabs the results and stuff it all in the cache
        for repo in repos_to_download:
            domain = urlparse(repo).hostname
            bg_downloader = bg_downloaders[domain]
            provider = bg_downloader.get_provider(repo)
            if not provider:
                continue

            unavailable_packages = []
            unavailable_libraries = []

            # Allow name mapping of packages for schema version < 2.0
            repository_packages = {}
            for name, info in provider.get_packages():
                name = name_map.get(name, name)
                info['name'] = name
                info['releases'] = filter_releases(name, self.settings, info['releases'])
                if info['releases']:
                    repository_packages[name] = info
                else:
                    unavailable_packages.append(name)

            repository_libraries = {}
            for name, info in provider.get_libraries():
                info['releases'] = filter_releases(name, self.settings, info['releases'])
                if info['releases']:
                    repository_libraries[name] = info
                else:
                    unavailable_libraries.append(name)

            # Display errors we encountered while fetching package info
            for url, exception in provider.get_failed_sources():
                console_write(exception)
            for name, exception in provider.get_broken_packages():
                console_write(exception)
            for name, exception in provider.get_broken_libraries():
                console_write(exception)

            cache_key = repo + '.packages'
            set_cache(cache_key, repository_packages, cache_ttl)
            packages.update(repository_packages)

            cache_key = repo + '.libraries'
            set_cache(cache_key, repository_libraries, cache_ttl)
            libraries.update(repository_libraries)

            renamed_packages = provider.get_renamed_packages()
            set_cache_under_settings(self, 'renamed_packages', repo, renamed_packages, cache_ttl)

            set_cache_under_settings(
                self,
                'unavailable_packages',
                repo,
                unavailable_packages,
                cache_ttl,
                list_=True
            )
            set_cache_under_settings(
                self,
                'unavailable_libraries',
                repo,
                unavailable_libraries,
                cache_ttl,
                list_=True
            )

        return (packages, libraries)

    def list_available_libraries(self, python_version):
        """
        Returns a master list of every available library from all sources that
        are compatible with the version of Python specified

        :param python_version:
            A unicode string of "3.3" or "3.8"

        :return:
            A dict in the format:
            {
                'Library Name': {
                    # library details - see example-repository.json for format
                },
                ...
            }
        """

        libraries = self._list_available()[1]
        filtered_libraries = {}
        for library_name in libraries:
            lib_info = libraries[library_name]
            filtered_releases = []
            for release in lib_info.get("releases", []):
                if "python_versions" not in release:
                    lib_python_compat = ["3.3"]
                else:
                    lib_python_compat = release["python_versions"]
                if python_version not in lib_python_compat:
                    continue
                filtered_releases.append(release)
            if not filtered_releases:
                continue
            filtered_libraries[library_name] = lib_info.copy()
            filtered_libraries[library_name]["releases"] = filtered_releases

        return filtered_libraries

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

        return self._list_available()[0]

    def list_packages(self, unpacked_only=False):
        """
        :param unpacked_only:
            Only list packages that are not inside of .sublime-package files

        :return: A list of all installed, non-default, non-library, package names
        """

        packages = self._list_visible_dirs(sys_path.packages_path)

        if unpacked_only is False:
            packages |= self._list_sublime_package_files(sys_path.installed_packages_path)

        packages -= set(self.list_default_packages())
        packages -= set(['User', 'Default'])
        return sorted(packages, key=lambda s: s.lower())

    def list_libraries(self):
        """
        :return:
            A list of library.Library() objects for all installed libraries
        """

        return library.list_all()

    def list_all_packages(self):
        """
        Lists all packages on the machine

        :return:
            A list of all installed package names, including default packages
        """

        packages = self.list_default_packages() + self.list_packages()
        return sorted(packages, key=lambda s: s.lower())

    def list_default_packages(self):
        """ :return: A list of all default package names"""

        app_dir = os.path.dirname(sublime.executable_path())
        packages = self._list_sublime_package_files(os.path.join(app_dir, 'Packages'))

        packages -= set(['User', 'Default'])
        return sorted(packages, key=lambda s: s.lower())

    def _list_visible_dirs(self, path):
        """
        Return a set of directories in the folder specified that are not
        hidden and are not marked to be removed

        :param path:
            The folder to list the directories inside of

        :return:
            A set of directory names
        """

        output = set()
        for filename in os.listdir(path):
            if filename[0] == '.':
                continue
            file_path = os.path.join(path, filename)
            if not os.path.isdir(file_path):
                continue
            # Don't include a dir if it is going to be cleaned up
            if os.path.exists(os.path.join(file_path, 'package-control.cleanup')):
                continue
            output.add(filename)
        return output

    def _list_sublime_package_files(self, path):
        """
        Return a set of all .sublime-package files in a folder

        :param path:
            The directory to look in for .sublime-package files

        :return:
            A set of the package names - i.e. with the .sublime-package suffix removed
        """

        output = set()
        if not os.path.exists(path):
            return output
        for filename in os.listdir(path):
            if not re.search(r'\.sublime-package$', filename):
                continue
            output.add(filename.replace('.sublime-package', ''))
        return output

    def find_required_libraries(self, ignore_package=None):
        """
        Find all of the libraries required by the installed packages,
        ignoring the specified package.

        :param ignore_package:
            The package to ignore when enumerating libraries

        :return:
            A list of library.Library() objects for the libraries required by
            the installed packages
        """

        output = set()
        for package in self.list_packages():
            if package == ignore_package:
                continue
            output |= self.get_libraries(package)
        return sorted(output)

    def get_package_dir(self, package_name):
        """:return: The full filesystem path to the package directory"""

        return os.path.join(sys_path.packages_path, package_name)

    def get_mapped_name(self, package_name):
        """:return: The name of the package after passing through mapping rules"""

        return self.settings.get('package_name_map', {}).get(package_name, package_name)

    def create_package(self, package_name, package_destination, profile=None):
        """
        Creates a .sublime-package file from the running Packages directory

        :param package_name:
            The package to create a .sublime-package file for

        :param package_destination:
            The full filesystem path of the directory to save the new
            .sublime-package file in.

        :param profile:
            If None, the "dirs_to_ignore", "files_to_ignore", "files_to_include"
            and "package_destination" settings will be used when creating the
            package. If a string, will look in the "package_profiles" setting
            and use the profile name to select a sub-dictionary which may
            contain all of the ignore/include settings.

        :return: bool if the package file was successfully created
        """

        package_dir = self.get_package_dir(package_name)
        if not os.path.isdir(package_dir):
            show_error(
                '''
                The folder for the package name specified, %s,
                does not exists in %s
                ''',
                (package_name, sys_path.packages_path)
            )
            return False

        package_filename = package_name + '.sublime-package'
        package_path = os.path.join(package_destination, package_filename)

        try:
            os.makedirs(package_destination, exist_ok=True)

            with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as package_file:

                compileall.compile_dir(package_dir, quiet=True, legacy=True, optimize=2)

                profile_settings = self.settings.get('package_profiles', {}).get(profile)

                def get_profile_setting(setting, default):
                    if profile_settings:
                        profile_value = profile_settings.get(setting)
                        if profile_value is not None:
                            return profile_value
                    return self.settings.get(setting, default)

                dirs_to_ignore = get_profile_setting('dirs_to_ignore', [])
                files_to_ignore = get_profile_setting('files_to_ignore', [])
                files_to_include = get_profile_setting('files_to_include', [])

                for root, dirs, files in os.walk(package_dir):
                    # remove all "dirs_to_ignore" from "dirs" to make os.walk ignore them
                    dirs[:] = [x for x in dirs if x not in dirs_to_ignore]
                    for file in files:
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, package_dir)

                        ignore_matches = (fnmatch(relative_path, p) for p in files_to_ignore)
                        include_matches = (fnmatch(relative_path, p) for p in files_to_include)
                        if any(ignore_matches) and not any(include_matches):
                            continue

                        package_file.write(full_path, relative_path)

        except (OSError, IOError) as e:
            show_error(
                '''
                An error occurred creating the package file %s in %s.

                %s
                ''',
                (package_filename, package_destination, str(e))
            )
            return False
        return True

    def _download_zip_file(self, name, url, tmp_zip_path):
        try:
            with downloader(url, self.settings) as manager:
                data = manager.fetch(url, 'Error downloading library.')
        except (DownloaderException) as e:
            console_write(e)
            show_error(
                '''
                Unable to download %s. Please view the console for
                more details.
                ''',
                name
            )
            return False

        with open(tmp_zip_path, "wb") as zf:
            zf.write(data)

        try:
            z = zipfile.ZipFile(tmp_zip_path, 'r')
        except (zipfile.BadZipfile):
            show_error(
                '''
                An error occurred while trying to unzip the file for %s.
                ''',
                name
            )
            return False

        return z

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

        root_level_paths = []
        last_path = None
        for path in zf.namelist():
            try:
                if not isinstance(path, str):
                    path = path.decode('utf-8', 'strict')
            except (UnicodeDecodeError):
                console_write(
                    '''
                    One or more of the zip file entries in %s is not
                    encoded using UTF-8, aborting
                    ''',
                    name
                )
                return False

            last_path = path

            if path.find('/') in [len(path) - 1, -1]:
                root_level_paths.append(path)
            # Make sure there are no paths that look like security vulnerabilities
            if path[0] == '/' or path.find('../') != -1 or path.find('..\\') != -1:
                show_error(
                    '''
                    The zip file for %s contains files that traverse outside
                    of the root and cannot be safely installed.
                    ''',
                    name
                )
                return False

        if last_path and len(root_level_paths) == 0:
            root_level_paths.append(last_path[0:last_path.find('/') + 1])

        # If there is only a single directory at the top leve, the file
        # is most likely a zip from BitBucket or GitHub and we need
        # to skip the top-level dir when extracting
        if len(root_level_paths) == 1 and root_level_paths[0].endswith('/'):
            return root_level_paths[0]

        return ""

    def _extract_zip(self, name, zf, dest_dir, extracted_dirs, extracted_files, common_folder):
        """
        Extracts a zip to a folder

        :param name:
            A unicode string of the package or library name

        :param zf:
            A zipfile instance to extract

        :param dest_dir:
            A unicode string of the destination directory

        :param extracted_dirs:
            A set of all of the dir paths extracted from the zip

        :param extracted_files:
            A set of all of the files paths extracted from the zip

        :param common_folder:
            A unicode string of a common folder name

        :return:
            A bool indication if the install should be retried
        """

        os.chdir(dest_dir)

        # Here we don't use .extractall() since it was having issues on OS X
        should_retry = False
        for info in zf.infolist():
            path = info.filename
            dest = path

            try:
                if not isinstance(dest, str):
                    dest = dest.decode('utf-8', 'strict')
            except (UnicodeDecodeError):
                console_write(
                    '''
                    One or more of the zip file entries in %s is not
                    encoded using UTF-8, aborting
                    ''',
                    name
                )
                return False

            if os.name == 'nt':
                regex = r':|\*|\?|"|<|>|\|'
                if re.search(regex, dest) is not None:
                    console_write(
                        '''
                        Skipping file from package named %s due to an
                        invalid filename
                        ''',
                        name
                    )
                    continue

            # If there was only a single directory in the package, we remove
            # that folder name from the paths as we extract entries
            dest = dest[len(common_folder):]

            if os.name == 'nt':
                dest = dest.replace('/', '\\')
            else:
                dest = dest.replace('\\', '/')

            dest = os.path.join(dest_dir, dest)

            def add_extracted_dirs(dir_):
                while dir_ not in extracted_dirs:
                    extracted_dirs.add(dir_)
                    dir_ = os.path.dirname(dir_)
                    if dir_ == dest_dir:
                        break

            if path.endswith('/'):
                os.makedirs(dest, exist_ok=True)
                add_extracted_dirs(dest)
            else:
                parent_dir = os.path.dirname(dest)
                os.makedirs(parent_dir, exist_ok=True)
                add_extracted_dirs(parent_dir)
                extracted_files.add(dest)
                try:
                    with open(dest, 'wb') as fobj:
                        fobj.write(zf.read(path))
                except (IOError) as e:
                    message = str(e)
                    if re.search('[Ee]rrno 13', message):
                        should_retry = True
                        break
                    console_write(
                        '''
                        Skipping file from package named %s due to an
                        invalid filename
                        ''',
                        name
                    )

                except (UnicodeDecodeError):
                    console_write(
                        '''
                        Skipping file from package named %s due to an
                        invalid filename
                        ''',
                        name
                    )
        return should_retry

    def install_library(self, library_name, python_version):
        libraries = self.list_available_libraries(python_version)

        is_available = library_name in list(libraries.keys())
        is_unavailable = library_name in self.settings.get('unavailable_libraries', [])

        if is_unavailable and not is_available:
            console_write(
                '''
                The library "%s" is either not available on this platform,
                for Python %s, or for this version of Sublime Text
                ''',
                (library_name, python_version)
            )
            # If a library is not available on this machine, that means it
            # is not needed
            return True

        if not is_available:
            console_write("The libary '%s' is not available for Python %s", (library_name, python_version))
            return False

        release = libraries[library_name]['releases'][0]

        url = release['url']
        suffix = '.whl' if url.endswith('.whl') else '.zip'
        library_filename = library_name + suffix

        tmp_dir = tempfile.mkdtemp('')

        try:
            # This is refers to the zipfile later on, so we define it here so we can
            # close the zip file if set during the finally clause
            library_zip = None

            tmp_library_archive = os.path.join(tmp_dir, library_filename)
            tmp_library_dir = os.path.join(tmp_dir, library_name)

            lib_path = sys_path.lib_paths()[python_version]
            existing_did = None
            try:
                existing_did = distinfo.find_dist_info_dir(lib_path, library_name)
                is_upgrade = True
            except FileNotFoundError:
                is_upgrade = False

            modified_paths = set()
            if is_upgrade:
                _, modified_ris = existing_did.verify_files()
                for mri in modified_ris:
                    modified_paths.add(mri.relative_path)

            if len(modified_paths):
                console_write(
                    "Unable to upgrade the libary '%s' because files on disk have been modified: '%s'",
                    (
                        library_name,
                        "', '".join(sorted(list(modified_paths)))
                    )
                )
                return False

            library_zip = self._download_zip_file(library_name, url, tmp_library_archive)
            if library_zip is False:
                return False

            common_folder = self._common_folder(library_name, library_zip)
            if common_folder is False:
                return False

            os.mkdir(tmp_library_dir)

            extracted_files = set()
            extracted_dirs = set()
            should_retry = self._extract_zip(
                library_name,
                library_zip,
                tmp_library_dir,
                extracted_dirs,
                extracted_files,
                common_folder
            )
            if should_retry:
                return False
            extracted_paths = extracted_files | extracted_dirs

            library_zip.close()
            library_zip = None

            new_did_name = '%s-%s.dist-info' % (library_name, release['version'])
            wheel_filename = new_did_name + '/WHEEL'
            is_whl = wheel_filename in extracted_paths

            if not is_whl:

                lib = libraries[library_name]
                try:
                    temp_did = library.convert_dependency(
                        tmp_library_dir,
                        python_version,
                        library_name,
                        release['version'],
                        lib.get('description'),
                        lib.get('homepage')
                    )
                except ValueError as e:
                    show_error(
                        '''
                        An error occurred while trying to install the library %s: %s
                        ''',
                        library_name,
                        str(e)
                    )
                    return False

            else:
                temp_did = distinfo.DistInfoDir(tmp_library_dir, new_did_name)

            new_did = distinfo.DistInfoDir(
                lib_path,
                "%s-%s.dist-info" % (library_name, release.get("version"))
            )
            new_did.ensure_exists()

            modified_paths = set()
            _, modified_ris = temp_did.verify_files()
            for mri in modified_ris:
                modified_paths.add(mri.absolute_path)

            if len(modified_paths):
                console_write(
                    "Unable to upgrade the libary '%s' because files in the archive have been modified: '%s'",
                    (
                        library_name,
                        "', '".join(sorted(list(modified_paths)))
                    )
                )
                return False

            if is_upgrade:
                try:
                    library.remove(existing_did.install_root, library_name)
                except OSError:
                    show_error(
                        '''
                        An error occurred while trying to upgrade the library %s. Please restart
                        Sublime Text to finish the upgrade.
                        ''',
                        library_name
                    )
                    return False

            library.install(temp_did, lib_path)

            os.chdir(sys_path.packages_path)
            return True

        finally:
            # We need to make sure the zipfile is closed to
            # help prevent permissions errors on Windows
            if library_zip:
                library_zip.close()

            # Try to remove the tmp dir after a second to make sure
            # a virus scanner is holding a reference to the zipfile
            # after we close it.
            sublime.set_timeout(lambda: unlink_or_delete_directory(tmp_dir), 1000)

    def install_package(self, package_name):
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

        :return: bool if the package was successfully installed or None
                 if the package needs to be cleaned up on the next restart
                 and should not be reenabled
        """

        packages = self.list_available_packages()

        is_available = package_name in list(packages.keys())
        is_unavailable = package_name in self.settings.get('unavailable_packages', [])

        if is_unavailable and not is_available:
            console_write(
                '''
                The package "%s" is either not available on this platform or for
                this version of Sublime Text
                ''',
                package_name
            )
            return False

        if not is_available:
            show_error("The package '%s' is not available", (package_name,))
            return False

        release = packages[package_name]['releases'][0]

        url = release['url']
        package_filename = package_name + '.sublime-package'

        tmp_dir = tempfile.mkdtemp('')

        try:
            # This is refers to the zipfile later on, so we define it here so we can
            # close the zip file if set during the finally clause
            package_zip = None

            tmp_package_path = os.path.join(tmp_dir, package_filename)

            unpacked_package_dir = self.get_package_dir(package_name)
            package_path = os.path.join(sys_path.installed_packages_path, package_filename)

            if self.is_vcs_package(package_name):
                # We explicitly don't support the "libraries" key when dealing
                # with packages installed via VCS

                upgrader = self.instantiate_upgrader(package_name)
                to_ignore = self.settings.get('ignore_vcs_packages')

                if to_ignore is True:
                    show_error(
                        '''
                        Skipping %s package %s since the setting
                        "ignore_vcs_packages" is set to true
                        ''',
                        (upgrader.cli_name, package_name)
                    )
                    return False

                if isinstance(to_ignore, list) and package_name in to_ignore:
                    show_error(
                        '''
                        Skipping %s package %s since it is listed in the
                        "ignore_vcs_packages" setting
                        ''',
                        (upgrader.cli_name, package_name)
                    )
                    return False

                result = upgrader.run()

                return result

            old_version = self.get_metadata(package_name).get('version')
            is_upgrade = old_version is not None

            package_zip = self._download_zip_file(package_name, url, tmp_package_path)
            if package_zip is False:
                return False

            common_folder = self._common_folder(package_name, package_zip)
            if common_folder is False:
                return False

            python_version_path = common_folder + '.python-version'
            libraries_path = common_folder + 'dependencies.json'
            no_package_file_zip_path = common_folder + '.no-sublime-package'

            # By default, ST prefers .sublime-package files since this allows
            # overriding files in the Packages/{package_name}/ folder.
            # If the package maintainer doesn't want a .sublime-package
            try:
                package_zip.getinfo(no_package_file_zip_path)
                unpack = True
            except (KeyError):
                unpack = False

            python_version = "3.3"
            try:
                python_version_raw = package_zip.read(python_version_path)
                if python_version_raw.decode('utf-8').strip() == "3.8":
                    python_version = "3.8"
            except (KeyError):
                pass

            have_installed_libraries = False
            libraries = release.get('libraries', [])
            if libraries:
                if not self.install_libraries(libraries, python_version):
                    return False
                have_installed_libraries = True

            # If libraries were not in the channel, try the package
            if not have_installed_libraries:
                try:
                    lib_info_json = package_zip.read(libraries_path)
                    lib_info = json.loads(lib_info_json.decode('utf-8'))
                except (KeyError):
                    lib_info = {}
                except (ValueError):
                    console_write(
                        '''
                        An error occurred while trying to parse the
                        dependencies.json for %s.
                        ''',
                        package_name
                    )
                    return False

                libraries = self.select_libraries(lib_info)
                if not self.install_libraries(libraries, python_version):
                    return False

            metadata_filename = 'package-metadata.json'

            # If we already have a package-metadata.json file in
            # Packages/{package_name}/, but the package no longer contains
            # a .no-sublime-package file, then we want to clear the unpacked
            # dir and install as a .sublime-package file. Since we are only
            # clearing if a package-metadata.json file exists, we should never
            # accidentally delete a user's customizations. However, we still
            # create a backup just in case.
            unpacked_metadata_file = os.path.join(unpacked_package_dir, metadata_filename)
            if os.path.exists(unpacked_metadata_file) and not unpack:
                self.backup_package_dir(package_name)
                if is_directory_symlink(unpacked_package_dir):
                    unlink_or_delete_directory(unpacked_package_dir)
                elif not clear_directory(unpacked_package_dir):
                    # If deleting failed, queue the package to upgrade upon next start
                    # where it will be disabled
                    reinstall_file = os.path.join(unpacked_package_dir, 'package-control.reinstall')
                    open(reinstall_file, 'wb').close()

                    # Don't delete the metadata file, that way we have it
                    # when the reinstall happens, and the appropriate
                    # usage info can be sent back to the server
                    clear_directory(unpacked_package_dir, {reinstall_file, unpacked_metadata_file})

                    show_error(
                        '''
                        An error occurred while trying to upgrade %s. Please
                        restart Sublime Text to finish the upgrade.
                        ''',
                        package_name
                    )
                    return None
                else:
                    unlink_or_delete_directory(unpacked_package_dir)

            # If we determined it should be unpacked, we extract directly
            # into the Packages/{package_name}/ folder
            if unpack:
                self.backup_package_dir(package_name)
                package_dir = unpacked_package_dir

            # Otherwise we go into a temp dir since we will be creating a
            # new .sublime-package file later
            else:
                tmp_working_dir = os.path.join(tmp_dir, 'working')
                os.mkdir(tmp_working_dir)
                package_dir = tmp_working_dir

            package_metadata_file = os.path.join(package_dir, metadata_filename)

            if not os.path.exists(package_dir):
                os.mkdir(package_dir)

            os.chdir(package_dir)

            extracted_files = set()
            extracted_dirs = set()
            should_retry = self._extract_zip(
                package_name,
                package_zip,
                package_dir,
                extracted_dirs,
                extracted_files,
                common_folder
            )
            extracted_paths = extracted_dirs | extracted_files

            package_zip.close()
            package_zip = None

            # If upgrading failed, queue the package to upgrade upon next start
            if should_retry:
                reinstall_file = os.path.join(package_dir, 'package-control.reinstall')
                open(reinstall_file, 'wb').close()

                # Don't delete the metadata file, that way we have it
                # when the reinstall happens, and the appropriate
                # usage info can be sent back to the server.
                # No need to handle symlink at this stage it was already removed
                # and we are not working with symlink here anymore.
                clear_directory(package_dir, {reinstall_file, package_metadata_file})

                show_error(
                    '''
                    An error occurred while trying to upgrade %s. Please restart
                    Sublime Text to finish the upgrade.
                    ''',
                    package_name
                )
                return None

            # Here we clean out any files that were not just overwritten. It is ok
            # if there is an error removing a file. The next time there is an
            # upgrade, it should be cleaned out successfully then.
            # No need to handle symlink at this stage it was already removed
            # and we are not working with symlink here anymore.
            clear_directory(package_dir, extracted_paths)

            new_version = release['version']

            self.print_messages(package_name, package_dir, is_upgrade, old_version, new_version)

            with open(package_metadata_file, 'w', encoding='utf-8') as fobj:
                url = packages[package_name]['homepage']
                metadata = {
                    "version": new_version,
                    "sublime_text": release['sublime_text'],
                    "platforms": release['platforms'],
                    "url": url,
                    "description": packages[package_name]['description'],
                    'libraries': release.get('libraries', [])
                }
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
            settings = sublime.load_settings(pc_settings_filename())
            names = load_list_setting(settings, 'installed_packages')
            if package_name not in names:
                names.append(package_name)
                save_list_setting(settings, pc_settings_filename(), 'installed_packages', names)

            # If we didn't extract directly into the Packages/{package_name}/
            # folder, we need to create a .sublime-package file and install it
            if not unpack:
                try:
                    # Remove the downloaded file since we are going to overwrite it
                    os.remove(tmp_package_path)
                    package_zip = zipfile.ZipFile(tmp_package_path, "w", compression=zipfile.ZIP_DEFLATED)
                except (OSError, IOError) as e:
                    show_error(
                        '''
                        An error occurred creating the package file %s in %s.

                        %s
                        ''',
                        (package_filename, tmp_dir, str(e))
                    )
                    return False

                package_dir_regex = re.compile('^' + re.escape(package_dir))
                for root, dirs, files in os.walk(package_dir):
                    paths = dirs
                    paths.extend(files)
                    for path in paths:
                        full_path = os.path.join(root, path)
                        relative_path = re.sub(package_dir_regex, '', full_path)
                        if os.path.isdir(full_path):
                            continue
                        package_zip.write(full_path, relative_path)

                package_zip.close()
                package_zip = None

                try:
                    if os.path.exists(package_path):
                        os.remove(package_path)
                    shutil.move(tmp_package_path, package_path)
                except (OSError):
                    new_package_path = package_path.replace('.sublime-package', '.sublime-package-new')
                    shutil.move(tmp_package_path, new_package_path)
                    show_error(
                        '''
                        An error occurred while trying to upgrade %s. Please restart
                        Sublime Text to finish the upgrade.
                        ''',
                        package_name
                    )
                    return None

            os.chdir(sys_path.packages_path)
            return True

        finally:
            # We need to make sure the zipfile is closed to
            # help prevent permissions errors on Windows
            if package_zip:
                package_zip.close()

            # Try to remove the tmp dir after a second to make sure
            # a virus scanner is holding a reference to the zipfile
            # after we close it.
            sublime.set_timeout(lambda: unlink_or_delete_directory(tmp_dir), 1000)

    def install_libraries(self, library_names, python_version, fail_early=True):
        """
        Ensures a list of libraries are installed and up-to-date

        :param library_names:
            A list of library names

        :param python_version:
            A unicode string of "3.3" or "3.8"

        :return:
            A boolean indicating if the libraries are properly installed
        """

        debug = self.settings.get('debug')

        available_libraries = self.list_available_libraries(python_version)

        lib_path = sys_path.lib_paths()[python_version]

        error = False
        for library_name in library_names:
            installed_version = None
            available_version = None

            def library_write(msg):
                msg = "The library '{library_name}' " + msg
                msg = msg.format(
                    library_name=library_name,
                    installed_version=installed_version,
                    available_version=available_version
                )
                console_write(msg)

            def library_write_debug(msg):
                if debug:
                    library_write(msg)

            if library_name not in available_libraries:
                library_write('is not available')
                if fail_early:
                    return False
                error = True
                continue

            info = available_libraries[library_name]

            try:
                existing_did = library.find_dist_info_dir(lib_path, library_name)
                installed_version = existing_did.read_metadata()['version']
            except FileNotFoundError:
                installed_version = None

            if installed_version:
                installed_version = library.PEP440Version(installed_version)

            library_releases = info.get('releases', [])
            library_release = library_releases[0] if library_releases else {}

            available_version = library_release.get('version')
            if available_version:
                available_version = library.PEP440Version(available_version)

            install_library = False
            if not installed_version:
                install_library = True
                library_write('is not currently installed; installing...')
            elif not library_releases:
                library_write('is installed, but there are no available releases; leaving alone')
            elif not available_version:
                library_write(
                    'is installed, but the latest available release '
                    'could not be determined; leaving alone'
                )
            elif installed_version < available_version:
                install_library = True
                library_write(
                    'is installed, but out of date; upgrading to latest '
                    'release {available_version} from {installed_version}...'
                )
            else:
                library_write_debug('is installed and up to date ({installed_version}); leaving alone')

            if install_library:
                library_result = self.install_library(library_name, python_version)
                if not library_result:
                    library_write('could not be installed or updated')
                    if fail_early:
                        return False
                    error = True
                else:
                    library_write('has successfully been installed or updated')

        return not error

    def cleanup_libraries(self, ignore_package=None, required_libraries=None):
        """
        Remove all not needed libraries by the installed packages,
        ignoring the specified package.

        :param ignore_package:
            The package to ignore when enumerating libraries.
            Not used when required_libraries is provided.

        :param required_libraries:
            All required libraries, for speedup purposes.

        :return:
            Boolean indicating the success of the removals.
        """

        installed_libraries = self.list_libraries()
        if not required_libraries:
            required_libraries = self.find_required_libraries(ignore_package)

        unmanaged_libraries = library.list_unmanaged()
        orphaned_libraries = sorted(set(installed_libraries) - set(required_libraries) - set(unmanaged_libraries))

        error = False
        for lib in orphaned_libraries:
            if self.remove_library(lib):
                console_write(
                    '''
                    The orphaned library %s for Python %s has been removed
                    ''',
                    (lib.name, lib.python_version)
                )
            else:
                error = True

        return not error

    def backup_package_dir(self, package_name):
        """
        Does a full backup of the Packages/{package}/ dir to Backup/

        :param package_name:
            The name of the package to back up

        :return:
            If the backup succeeded
        """

        package_dir = os.path.join(sys_path.packages_path, package_name)
        if not os.path.exists(package_dir):
            return True

        try:
            backup_dir = os.path.join(os.path.dirname(
                sys_path.packages_path), 'Backup',
                datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
            os.makedirs(backup_dir, exist_ok=True)
            package_backup_dir = os.path.join(backup_dir, package_name)
            if os.path.exists(package_backup_dir):
                console_write(
                    '''
                    Backup folder "%s" already exists!
                    ''',
                    package_backup_dir
                )
            shutil.copytree(package_dir, package_backup_dir)
            return True

        except (OSError, IOError) as e:
            show_error(
                '''
                An error occurred while trying to backup the package directory
                for %s.

                %s
                ''',
                (package_name, str(e))
            )
            try:
                if os.path.exists(package_backup_dir):
                    unlink_or_delete_directory(package_backup_dir)
            except (UnboundLocalError):
                pass  # Exeption occurred before package_backup_dir defined
            return False

    def print_messages(self, package_name, package_dir, is_upgrade, old_version, new_version):
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
        """

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
            with open(message_path, 'r', encoding='utf-8', errors='replace') as fobj:
                return '\n  %s\n' % fobj.read().rstrip().replace('\n', '\n  ')

        output = ''
        if not is_upgrade and message_info.get('install'):
            try:
                install_file = message_info.get('install')
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
            upgrade_messages = list(set(message_info.keys()) - set(['install']))
            upgrade_messages = version_sort(upgrade_messages, reverse=True)
            old_version_cmp = version_comparable(old_version)
            new_version_cmp = version_comparable(new_version)

            for version in upgrade_messages:
                version_cmp = version_comparable(version)
                if version_cmp <= old_version_cmp:
                    break
                # If the package developer sets up release notes for future
                # versions, we don't want to show them for every release
                if version_cmp > new_version_cmp:
                    continue

                try:
                    upgrade_file = message_info.get(version)
                    upgrade_path = os.path.join(package_dir, upgrade_file)
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
        else:
            output = '\n\n%s\n%s\n' % (package_name, '-' * len(package_name)) + output

        def print_to_panel():
            window = sublime.active_window()

            views = window.views()
            view = None
            for _view in views:
                if _view.name() == 'Package Control Messages':
                    view = _view
                    break

            if not view:
                view = window.new_file()
                view.set_name('Package Control Messages')
                view.set_scratch(True)
                view.settings().set("word_wrap", True)
                view.settings().set("auto_indent", False)
                view.settings().set("tab_width", 2)
            else:
                view.set_read_only(False)
                if window.active_view() != view:
                    window.focus_view(view)

            def write(string):
                view.run_command('insert', {'characters': string})

            old_sel = list(view.sel())
            old_vpos = view.viewport_position()

            size = view.size()
            view.sel().clear()
            view.sel().add(sublime.Region(size, size))

            if not view.size():
                write(text.format(
                    '''
                    Package Control Messages
                    ========================
                    '''
                ))
            write(output)

            # Move caret to the new end of the file if it was previously
            if sublime.Region(size, size) == old_sel[-1]:
                old_sel[-1] = sublime.Region(view.size(), view.size())

            view.sel().clear()
            for reg in old_sel:
                view.sel().add(reg)

            view.set_viewport_position(old_vpos, False)
            view.set_read_only(True)

        sublime.set_timeout(print_to_panel, 1)

    def remove_library(self, lib):
        """
        Deletes a library

        :param lib:
            The library.Library() to delete

        :return:
            bool if the library was successfully deleted
        """

        installed_libraries = self.list_libraries()

        if lib not in set(installed_libraries):
            show_error(
                '''
                The library specified, %s for Python %s, is not installed
                ''',
                (lib.name, lib.python_version)
            )
            return False

        lib_path = sys_path.lib_paths()[lib.python_version]
        try:
            library.remove(lib_path, lib.name)
        except OSError:
            # THe way library.remove() works is that the .dist-info dir is
            # removed last. This means that any permissions errors will happen
            # before we remove the metadata, and thus we'll still think the
            # library is installed when ST restarts, and we can try removing
            # it again in the future.
            show_error(
                '''
                An error occurred while trying to remove the library %s for
                Python %s. Please restart Sublime Text to finish the cleanup.
                ''',
                (lib.name, lib.python_version)
            )
            return False

    def remove_package(self, package_name):
        """
        Deletes a package

        The deletion process consists of:

        1. Deleting the directory (or marking it for deletion if deletion fails)
        2. Submitting usage info
        3. Removing the package from the list of installed packages

        :param package_name:
            The package to delete

        :return: bool if the package was successfully deleted or None
                 if the package needs to be cleaned up on the next restart
                 and should not be reenabled
        """

        installed_packages = self.list_packages()

        if package_name not in installed_packages:
            show_error(
                '''
                The package specified, %s, is not installed
                ''',
                (package_name,)
            )
            return False

        os.chdir(sys_path.packages_path)

        package_filename = package_name + '.sublime-package'
        installed_package_path = os.path.join(sys_path.installed_packages_path, package_filename)
        package_dir = self.get_package_dir(package_name)

        version = self.get_metadata(package_name).get('version')

        cleanup_complete = True

        try:
            if os.path.exists(installed_package_path):
                os.remove(installed_package_path)
        except (OSError, IOError):
            cleanup_complete = False

        if os.path.exists(package_dir):
            # We don't delete the actual package dir immediately due to a bug
            # in sublime_plugin.py
            can_delete_dir = True
            if is_directory_symlink(package_dir):
                # Assuming that deleting symlink won't fail in later step so
                # not having any cleanup handling here
                pass
            elif not clear_directory(package_dir):
                # If there is an error deleting now, we will mark it for
                # cleanup the next time Sublime Text starts
                open(os.path.join(package_dir, 'package-control.cleanup'), 'wb').close()
                cleanup_complete = False
                can_delete_dir = False

        params = {
            'package': package_name,
            'operation': 'remove',
            'version': version
        }
        self.record_usage(params)

        settings = sublime.load_settings(pc_settings_filename())
        names = load_list_setting(settings, 'installed_packages')
        if package_name in names:
            names.remove(package_name)
            save_list_setting(settings, pc_settings_filename(), 'installed_packages', names)

        if os.path.exists(package_dir) and can_delete_dir:
            unlink_or_delete_directory(package_dir)

        message = 'The package %s has been removed' % package_name
        if not cleanup_complete:
            message += ' and will be cleaned up on the next restart'
        console_write(message)

        # Remove libraries that are no longer needed
        self.cleanup_libraries(package_name)

        return True if cleanup_complete else None

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
        params['package_control_version'] = \
            self.get_metadata('Package Control').get('version')
        params['sublime_platform'] = self.settings.get('platform')
        params['sublime_version'] = self.settings.get('version')

        # For Python 2, we need to explicitly encoding the params
        for param in params:
            if isinstance(params[param], str):
                params[param] = params[param].encode('utf-8')

        url = self.settings.get('submit_url') + '?' + urlencode(params)

        try:
            with downloader(url, self.settings) as manager:
                result = manager.fetch(url, 'Error submitting usage information.')
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
