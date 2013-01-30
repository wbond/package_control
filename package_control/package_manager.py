try:
    # Python 3
    from urllib.parse import urlparse, urlencode
    import urllib.request as urllib_compat
except (ImportError):
    # Python 2
    from urlparse import urlparse
    from urllib import urlencode
    import urllib2 as urllib_compat

import sublime
import sys
import os
import re
import socket
import json
import time
import zipfile
import shutil
from fnmatch import fnmatch
import datetime

try:
    # Python 3
    from ..lib.all import semver
except (ValueError):
    # Python 2
    import semver

from .show_error import show_error
from .console_write import console_write
from .open_compat import open_compat, read_compat
from .unicode import unicode_from_os
from .clear_directory import clear_directory
from .cache import set_cache, get_cache

from .downloaders.urllib2_downloader import UrlLib2Downloader
from .downloaders.wget_downloader import WgetDownloader
from .downloaders.curl_downloader import CurlDownloader
from .downloaders.repository_downloader import RepositoryDownloader
from .downloaders.binary_not_found_error import BinaryNotFoundError

from .providers.channel_provider import ChannelProvider

from .http.rate_limit_exception import RateLimitException

from .upgraders.git_upgrader import GitUpgrader
from .upgraders.hg_upgrader import HgUpgrader


# The providers (in order) to check when trying to download a channel
_channel_providers = [ChannelProvider]


class PackageManager():
    """
    Allows downloading, creating, installing, upgrading, and deleting packages

    Delegates metadata retrieval to the _channel_providers and
    _package_providers classes. Uses VcsUpgrader-based classes for handling
    git and hg repositories in the Packages folder. Downloader classes are
    utilized to fetch contents of URLs.

    Also handles displaying package messaging, and sending usage information to
    the usage server.
    """

    def __init__(self):
        # Here we manually copy the settings since sublime doesn't like
        # code accessing settings from threads
        self.settings = {}
        settings = sublime.load_settings('Package Control.sublime-settings')
        for setting in ['timeout', 'repositories', 'repository_channels',
                'package_name_map', 'dirs_to_ignore', 'files_to_ignore',
                'package_destination', 'cache_length', 'auto_upgrade',
                'files_to_ignore_binary', 'files_to_keep', 'dirs_to_keep',
                'git_binary', 'git_update_command', 'hg_binary',
                'hg_update_command', 'http_proxy', 'https_proxy',
                'auto_upgrade_ignore', 'auto_upgrade_frequency',
                'submit_usage', 'submit_url', 'renamed_packages',
                'files_to_include', 'files_to_include_binary', 'certs',
                'ignore_vcs_packages', 'proxy_username', 'proxy_password',
                'debug', 'user_agent']:
            if settings.get(setting) == None:
                continue
            self.settings[setting] = settings.get(setting)

        # https_proxy will inherit from http_proxy unless it is set to a
        # string value or false
        no_https_proxy = self.settings.get('https_proxy') in ["", None]
        if no_https_proxy and self.settings.get('http_proxy'):
            self.settings['https_proxy'] = self.settings.get('http_proxy')
        if self.settings['https_proxy'] == False:
            self.settings['https_proxy'] = ''

        self.settings['platform'] = sublime.platform()
        self.settings['version'] = sublime.version()

    def compare_versions(self, version1, version2):
        """
        Compares to version strings to see which is greater

        Date-based version numbers (used by GitHub and BitBucket providers)
        are automatically pre-pended with a 0 so they are always less than
        version 1.0.

        :return:
            -1  if version1 is less than version2
             0  if they are equal
             1  if version1 is greater than version2
        """

        def date_compat(v):
            # We prepend 0 to all date-based version numbers so that developers
            # may switch to explicit versioning from GitHub/BitBucket
            # versioning based on commit dates
            date_match = re.match('(\d{4})\.(\d{2})\.(\d{2})\.(\d{2})\.(\d{2})\.(\d{2})$', v)
            if date_match:
                v = '0.%s.%s.%s.%s.%s.%s' % date_match.groups()
            return v

        def semver_compat(v):
            # When translating dates into semver, the way to get each date
            # segment into the version is to treat the year and month as
            # minor and patch, and then the rest as a numeric build version
            # with four different parts. The result looks like:
            # 0.2012.11+10.31.23.59
            date_match = re.match('(\d{4}(?:\.\d{2}){2})\.(\d{2}(?:\.\d{2}){3})$', v)
            if date_match:
                v = '%s+%s' % (date_match.group(1), date_match.group(2))

            # Semver must have major, minor, patch
            elif re.match('^\d+$', v):
                v += '.0.0'
            elif re.match('^\d+\.\d+$', v):
                v += '.0'
            return v

        def cmp_compat(v):
            return [int(x) for x in re.sub(r'(\.0+)*$', '', v).split(".")]

        version1 = date_compat(version1)
        version2 = date_compat(version2)
        try:
            return semver.compare(semver_compat(version1), semver_compat(version2))
        except (ValueError):
            cv1 = cmp_compat(version1)
            cv2 = cmp_compat(version2)
            return (cv1 > cv2) - (cv1 < cv2)

    def download_url(self, url, error_message):
        """
        Downloads a URL and returns the contents

        :param url:
            The string URL to download

        :param error_message:
            The error message to include if the download fails

        :return:
            The string contents of the URL, or False on error
        """

        has_ssl = 'ssl' in sys.modules and hasattr(urllib_compat, 'HTTPSHandler')
        is_ssl = re.search('^https://', url) != None
        downloader = None

        if (is_ssl and has_ssl) or not is_ssl:
            downloader = UrlLib2Downloader(self.settings)
        else:
            for downloader_class in [CurlDownloader, WgetDownloader]:
                try:
                    downloader = downloader_class(self.settings)
                    break
                except (BinaryNotFoundError):
                    pass

        if not downloader:
            show_error(u'Unable to download %s due to no ssl module available and no capable program found. Please install curl or wget.' % url)
            return False

        url = url.replace(' ', '%20')
        hostname = urlparse(url).hostname.lower()
        timeout = self.settings.get('timeout', 3)

        rate_limited_domains = get_cache('rate_limited_domains', [])

        if self.settings.get('debug'):
            try:
                ip = socket.gethostbyname(hostname)
            except (socket.gaierror) as e:
                ip = unicode_from_os(e)

            console_write(u"Download Debug", True)
            console_write(u"  URL: %s" % url)
            console_write(u"  Resolved IP: %s" % ip)
            console_write(u"  Timeout: %s" % str(timeout))

        if hostname in rate_limited_domains:
            if self.settings.get('debug'):
                console_write(u"  Skipping due to hitting rate limit for %s" % hostname)
            return False

        try:
            return downloader.download(url, error_message, timeout, 3)
        except (RateLimitException) as e:

            rate_limited_domains.append(hostname)
            set_cache('rate_limited_domains', rate_limited_domains, self.settings.get('cache_length'))

            error_string = (u'Hit rate limit of %s for %s, skipping all futher ' +
                u'download requests for this domain') % (e.limit, e.host)
            console_write(error_string, True)

        return False

    def get_metadata(self, package):
        """
        Returns the package metadata for an installed package

        :return:
            A dict with the keys:
                version
                url
                description
            or an empty dict on error
        """

        metadata_filename = os.path.join(self.get_package_dir(package),
            'package-metadata.json')
        if os.path.exists(metadata_filename):
            with open_compat(metadata_filename) as f:
                try:
                    return json.loads(read_compat(f))
                except (ValueError):
                    return {}
        return {}

    def list_repositories(self):
        """
        Returns a master list of all repositories pulled from all sources

        These repositories come from the channels specified in the
        "repository_channels" setting, plus any repositories listed in the
        "repositories" setting.

        :return:
            A list of all available repositories
        """

        cache_ttl = self.settings.get('cache_length')

        repositories = self.settings.get('repositories')
        repository_channels = self.settings.get('repository_channels')
        for channel in repository_channels:
            channel = channel.strip()

            # Caches various info from channels for performance
            cache_key = channel + '.repositories'
            channel_repositories = get_cache(cache_key)

            name_map_cache_key = channel + '.package_name_map'
            name_map = get_cache('name_map_cache_key')
            if name_map:
                name_map.update(self.settings.get('package_name_map', {}))
                self.settings['package_name_map'] = name_map

            renamed_cache_key = channel + '.renamed_packages'
            renamed_packages = get_cache(renamed_cache_key)
            if renamed_packages:
                renamed_packages.update(self.settings.get('renamed_packages', {}))
                self.settings['renamed_packages'] = renamed_packages

            unavailable_cache_key = channel + '.unavailable_packages'
            unavailable_packages = get_cache(unavailable_cache_key)
            if unavailable_packages:
                unavailable_packages.extend(self.settings.get('unavailable_packages', []))
                self.settings['unavailable_packages'] = unavailable_packages

            certs_cache_key = channel + '.certs'
            certs = self.settings.get('certs', {})
            channel_certs = get_cache('certs_cache_key')
            if channel_certs:
                certs.update(channel_certs)
                self.settings['certs'] = certs

            # If any of the info was not retrieved from the cache, we need to
            # grab the channel to get it
            if channel_repositories == None or \
                    self.settings.get('package_name_map') == None or \
                    self.settings.get('renamed_packages') == None:

                for provider_class in _channel_providers:
                    provider = provider_class(channel, self)
                    if provider.match_url():
                        break

                channel_repositories = provider.get_repositories()
                if channel_repositories == False:
                    continue
                set_cache(cache_key, channel_repositories, cache_ttl)

                for repo in channel_repositories:
                    if provider.get_packages(repo) == False:
                        continue
                    packages_cache_key = repo + '.packages'
                    set_cache(packages_cache_key, provider.get_packages(repo), cache_ttl)

                # Have the local name map override the one from the channel
                name_map = provider.get_name_map()
                name_map.update(self.settings.get('package_name_map', {}))
                self.settings['package_name_map'] = name_map
                set_cache(name_map_cache_key, name_map, cache_ttl)

                renamed_packages = provider.get_renamed_packages()
                set_cache(renamed_cache_key, renamed_packages, cache_ttl)
                if renamed_packages:
                    self.settings['renamed_packages'] = self.settings.get('renamed_packages', {})
                    self.settings['renamed_packages'].update(renamed_packages)

                unavailable_packages = provider.get_unavailable_packages()
                set_cache(unavailable_cache_key, unavailable_packages, cache_ttl)
                if unavailable_packages:
                    self.settings['unavailable_packages'] = self.settings.get('unavailable_packages', [])
                    self.settings['unavailable_packages'].extend(unavailable_packages)

                certs = provider.get_certs()
                set_cache(certs_cache_key, certs, cache_ttl)
                if certs:
                    self.settings['certs'] = self.settings.get('certs', {})
                    self.settings['certs'].update(certs)

            repositories.extend(channel_repositories)
        return [repo.strip() for repo in repositories]

    def list_available_packages(self):
        """
        Returns a master list of every available package from all sources

        :return:
            A dict in the format:
            {
                'Package Name': {
                    # Package details - see example-packages.json for format
                },
                ...
            }
        """

        cache_ttl = self.settings.get('cache_length')
        repositories = self.list_repositories()
        packages = {}
        downloaders = []
        grouped_downloaders = {}

        # Repositories are run in reverse order so that the ones first
        # on the list will overwrite those last on the list
        for repo in repositories[::-1]:
            cache_key = repo + '.packages'
            repository_packages = get_cache(cache_key)
            if repository_packages:
                packages.update(repository_packages)

            if repository_packages == None:
                downloader = RepositoryDownloader(self,
                    self.settings.get('package_name_map', {}), repo)
                domain = re.sub('^https?://[^/]*?(\w+\.\w+)($|/.*$)', '\\1',
                    repo)

                # downloaders are grouped by domain so that multiple can
                # be run in parallel without running into API access limits
                if not grouped_downloaders.get(domain):
                    grouped_downloaders[domain] = []
                grouped_downloaders[domain].append(downloader)

        # Allows creating a separate named function for each downloader
        # delay. Not having this contained in a function causes all of the
        # schedules to reference the same downloader.start()
        def schedule(downloader, delay):
            downloader.has_started = False

            def inner():
                downloader.start()
                downloader.has_started = True
            sublime.set_timeout(inner, delay)

        # Grabs every repo grouped by domain and delays the start
        # of each download from that domain by a fixed amount
        for domain_downloaders in list(grouped_downloaders.values()):
            for i in range(len(domain_downloaders)):
                downloader = domain_downloaders[i]
                downloaders.append(downloader)
                schedule(downloader, i * 150)

        complete = []

        # Wait for all of the downloaders to finish
        while downloaders:
            downloader = downloaders.pop()
            if downloader.has_started:
                downloader.join()
                complete.append(downloader)
            else:
                downloaders.insert(0, downloader)

        # Grabs the results and stuff if all in the cache
        for downloader in complete:
            repository_packages = downloader.packages
            if repository_packages == False:
                continue
            cache_key = downloader.repo + '.packages'
            set_cache(cache_key, repository_packages, cache_ttl)
            packages.update(repository_packages)

            renamed_packages = downloader.renamed_packages
            if renamed_packages == False:
                continue
            renamed_cache_key = downloader.repo + '.renamed_packages'
            set_cache(renamed_cache_key, renamed_packages, cache_ttl)
            if renamed_packages:
                self.settings['renamed_packages'] = self.settings.get('renamed_packages', {})
                self.settings['renamed_packages'].update(renamed_packages)

            unavailable_packages = downloader.unavailable_packages
            unavailable_cache_key = downloader.repo + '.unavailable_packages'
            set_cache(unavailable_cache_key, unavailable_packages, cache_ttl)
            if unavailable_packages:
                self.settings['unavailable_packages'] = self.settings.get('unavailable_packages', [])
                self.settings['unavailable_packages'].extend(unavailable_packages)

        return packages

    def list_packages(self):
        """ :return: A list of all installed, non-default, package names"""

        package_names = os.listdir(sublime.packages_path())
        package_names = [path for path in package_names if
            os.path.isdir(os.path.join(sublime.packages_path(), path))]

        # Ignore things to be deleted
        ignored = []
        for package in package_names:
            cleanup_file = os.path.join(sublime.packages_path(), package,
                'package-control.cleanup')
            if os.path.exists(cleanup_file):
                ignored.append(package)

        packages = list(set(package_names) - set(ignored) -
            set(self.list_default_packages()))
        packages = sorted(packages, key=lambda s: s.lower())

        return packages

    def list_all_packages(self):
        """ :return: A list of all installed package names, including default packages"""

        packages = os.listdir(sublime.packages_path())
        packages = sorted(packages, key=lambda s: s.lower())
        return packages

    def list_default_packages(self):
        """ :return: A list of all default package names"""

        if int(sublime.version()) > 3000:
            bundled_packages_path = os.path.join(os.path.dirname(sublime.executable_path()),
                'Packages')
            files = os.listdir(bundled_packages_path)
        else:
            files = os.listdir(os.path.join(os.path.dirname(
                sublime.packages_path()), 'Pristine Packages'))
            files = list(set(files) - set(os.listdir(
                sublime.installed_packages_path())))
        packages = [file.replace('.sublime-package', '') for file in files]
        packages = sorted(packages, key=lambda s: s.lower())
        return packages

    def get_package_dir(self, package):
        """:return: The full filesystem path to the package directory"""

        return os.path.join(sublime.packages_path(), package)

    def get_mapped_name(self, package):
        """:return: The name of the package after passing through mapping rules"""

        return self.settings.get('package_name_map', {}).get(package, package)

    def create_package(self, package_name, package_destination,
            binary_package=False):
        """
        Creates a .sublime-package file from the running Packages directory

        :param package_name:
            The package to create a .sublime-package file for

        :param package_destination:
            The full filesystem path of the directory to save the new
            .sublime-package file in.

        :param binary_package:
            If the created package should follow the binary package include/
            exclude patterns from the settings. These normally include a setup
            to exclude .py files and include .pyc files, but that can be
            changed via settings.

        :return: bool if the package file was successfully created
        """

        package_dir = self.get_package_dir(package_name) + '/'

        if not os.path.exists(package_dir):
            show_error(u'The folder for the package name specified, %s, does not exist in %s' % (
                package_name, sublime.packages_path()))
            return False

        package_filename = package_name + '.sublime-package'
        package_path = os.path.join(package_destination,
            package_filename)

        if not os.path.exists(sublime.installed_packages_path()):
            os.mkdir(sublime.installed_packages_path())

        if os.path.exists(package_path):
            os.remove(package_path)

        try:
            package_file = zipfile.ZipFile(package_path, "w",
                compression=zipfile.ZIP_DEFLATED)
        except (OSError, IOError) as e:
            show_error(u'An error occurred creating the package file %s in %s.\n\n%s' % (
                package_filename, package_destination, unicode_from_os(e)))
            return False

        dirs_to_ignore = self.settings.get('dirs_to_ignore', [])
        if not binary_package:
            files_to_ignore = self.settings.get('files_to_ignore', [])
            files_to_include = self.settings.get('files_to_include', [])
        else:
            files_to_ignore = self.settings.get('files_to_ignore_binary', [])
            files_to_include = self.settings.get('files_to_include_binary', [])

        package_dir_regex = re.compile('^' + re.escape(package_dir))
        for root, dirs, files in os.walk(package_dir):
            [dirs.remove(dir) for dir in dirs if dir in dirs_to_ignore]
            paths = dirs
            paths.extend(files)
            for path in paths:
                full_path = os.path.join(root, path)
                relative_path = re.sub(package_dir_regex, '', full_path)

                ignore_matches = [fnmatch(relative_path, p) for p in files_to_ignore]
                include_matches = [fnmatch(relative_path, p) for p in files_to_include]
                if any(ignore_matches) and not any(include_matches):
                    continue

                if os.path.isdir(full_path):
                    continue
                package_file.write(full_path, relative_path)

        package_file.close()

        return True

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

        :return: bool if the package was successfully installed
        """

        packages = self.list_available_packages()

        if package_name in self.settings.get('unavailable_packages', []):
            console_write(u'The package "%s" is not available on this platform.' % package_name, True)
            return False

        if package_name not in list(packages.keys()):
            show_error(u'The package specified, %s, is not available' % package_name)
            return False

        download = packages[package_name]['downloads'][0]
        url = download['url']

        package_filename = package_name + \
            '.sublime-package'
        package_path = os.path.join(sublime.installed_packages_path(),
            package_filename)
        pristine_package_path = os.path.join(os.path.dirname(
            sublime.packages_path()), 'Pristine Packages', package_filename)

        package_dir = self.get_package_dir(package_name)

        package_metadata_file = os.path.join(package_dir,
            'package-metadata.json')

        if os.path.exists(os.path.join(package_dir, '.git')):
            if self.settings.get('ignore_vcs_packages'):
                show_error(u'Skipping git package %s since the setting ignore_vcs_packages is set to true' % package_name)
                return False
            return GitUpgrader(self.settings['git_binary'],
                self.settings['git_update_command'], package_dir,
                self.settings['cache_length'], self.settings['debug']).run()
        elif os.path.exists(os.path.join(package_dir, '.hg')):
            if self.settings.get('ignore_vcs_packages'):
                show_error(u'Skipping hg package %s since the setting ignore_vcs_packages is set to true' % package_name)
                return False
            return HgUpgrader(self.settings['hg_binary'],
                self.settings['hg_update_command'], package_dir,
                self.settings['cache_length'], self.settings['debug']).run()

        is_upgrade = os.path.exists(package_metadata_file)
        old_version = None
        if is_upgrade:
            old_version = self.get_metadata(package_name).get('version')

        package_bytes = self.download_url(url, 'Error downloading package.')
        if package_bytes == False:
            return False
        with open_compat(package_path, "wb") as package_file:
            package_file.write(package_bytes)

        if not os.path.exists(package_dir):
            os.mkdir(package_dir)

        # We create a backup copy incase something was edited
        else:
            try:
                backup_dir = os.path.join(os.path.dirname(
                    sublime.packages_path()), 'Backup',
                    datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir)
                package_backup_dir = os.path.join(backup_dir, package_name)
                shutil.copytree(package_dir, package_backup_dir)
            except (OSError, IOError) as e:
                show_error(u'An error occurred while trying to backup the package directory for %s.\n\n%s' % (
                    package_name, unicode_from_os(e)))
                shutil.rmtree(package_backup_dir)
                return False

        try:
            package_zip = zipfile.ZipFile(package_path, 'r')
        except (zipfile.BadZipfile):
            show_error(u'An error occurred while trying to unzip the package file for %s. Please try installing the package again.' % package_name)
            return False

        root_level_paths = []
        last_path = None
        for path in package_zip.namelist():
            last_path = path
            if path.find('/') in [len(path) - 1, -1]:
                root_level_paths.append(path)
            if path[0] == '/' or path.find('../') != -1 or path.find('..\\') != -1:
                show_error(u'The package specified, %s, contains files outside of the package dir and cannot be safely installed.' % package_name)
                return False

        if last_path and len(root_level_paths) == 0:
            root_level_paths.append(last_path[0:last_path.find('/') + 1])

        os.chdir(package_dir)

        overwrite_failed = False

        # Here we don't use .extractall() since it was having issues on OS X
        skip_root_dir = len(root_level_paths) == 1 and \
            root_level_paths[0].endswith('/')
        extracted_paths = []
        for path in package_zip.namelist():
            dest = path
            try:
                # Python 3 seems to return the paths as str instead of
                # bytes, so we only need this for Python 2
                if int(sublime.version()) < 3000 and not isinstance(dest, unicode):
                    dest = unicode(dest, 'utf-8', 'strict')
            except (UnicodeDecodeError):
                dest = unicode(dest, 'cp1252', 'replace')

            if os.name == 'nt':
                regex = ':|\*|\?|"|<|>|\|'
                if re.search(regex, dest) != None:
                    console_write(u'Skipping file from package named %s due to an invalid filename' % path, True)
                    continue

            # If there was only a single directory in the package, we remove
            # that folder name from the paths as we extract entries
            if skip_root_dir:
                dest = dest[len(root_level_paths[0]):]

            if os.name == 'nt':
                dest = dest.replace('/', '\\')
            else:
                dest = dest.replace('\\', '/')

            dest = os.path.join(package_dir, dest)

            def add_extracted_dirs(dir):
                while dir not in extracted_paths:
                    extracted_paths.append(dir)
                    dir = os.path.dirname(dir)
                    if dir == package_dir:
                        break

            if path.endswith('/'):
                if not os.path.exists(dest):
                    os.makedirs(dest)
                add_extracted_dirs(dest)
            else:
                dest_dir = os.path.dirname(dest)
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                add_extracted_dirs(dest_dir)
                extracted_paths.append(dest)
                try:
                    open_compat(dest, 'wb').write(package_zip.read(path))
                except (IOError) as e:
                    message = unicode_from_os(e)
                    if re.search('[Ee]rrno 13', message):
                        overwrite_failed = True
                        break
                    console_write(u'Skipping file from package named %s due to an invalid filename' % path, True)

                except (UnicodeDecodeError):
                    console_write(u'Skipping file from package named %s due to an invalid filename' % path, True)
        package_zip.close()

        # If upgrading failed, queue the package to upgrade upon next start
        if overwrite_failed:
            reinstall_file = os.path.join(package_dir, 'package-control.reinstall')
            open_compat(reinstall_file, 'w').close()

            # Don't delete the metadata file, that way we have it
            # when the reinstall happens, and the appropriate
            # usage info can be sent back to the server
            clear_directory(package_dir, [reinstall_file, package_metadata_file])

            show_error(u'An error occurred while trying to upgrade %s. Please restart Sublime Text to finish the upgrade.' % package_name)
            return False

        # Here we clean out any files that were not just overwritten. It is ok
        # if there is an error removing a file. The next time there is an
        # upgrade, it should be cleaned out successfully then.
        clear_directory(package_dir, extracted_paths)

        self.print_messages(package_name, package_dir, is_upgrade, old_version)

        with open_compat(package_metadata_file, 'w') as f:
            metadata = {
                "version": packages[package_name]['downloads'][0]['version'],
                "url": packages[package_name]['url'],
                "description": packages[package_name]['description']
            }
            json.dump(metadata, f)

        # Submit install and upgrade info
        if is_upgrade:
            params = {
                'package': package_name,
                'operation': 'upgrade',
                'version': packages[package_name]['downloads'][0]['version'],
                'old_version': old_version
            }
        else:
            params = {
                'package': package_name,
                'operation': 'install',
                'version': packages[package_name]['downloads'][0]['version']
            }
        self.record_usage(params)

        # Record the install in the settings file so that you can move
        # settings across computers and have the same packages installed
        def save_package():
            settings = sublime.load_settings('Package Control.sublime-settings')
            installed_packages = settings.get('installed_packages', [])
            if not installed_packages:
                installed_packages = []
            installed_packages.append(package_name)
            installed_packages = list(set(installed_packages))
            installed_packages = sorted(installed_packages,
                key=lambda s: s.lower())
            settings.set('installed_packages', installed_packages)
            sublime.save_settings('Package Control.sublime-settings')
        sublime.set_timeout(save_package, 1)

        # Here we delete the package file from the installed packages directory
        # since we don't want to accidentally overwrite user changes
        os.remove(package_path)
        # We have to remove the pristine package too or else Sublime Text 2
        # will silently delete the package
        if os.path.exists(pristine_package_path):
            os.remove(pristine_package_path)

        os.chdir(sublime.packages_path())
        return True

    def print_messages(self, package, package_dir, is_upgrade, old_version):
        """
        Prints out package install and upgrade messages

        The functionality provided by this allows package maintainers to
        show messages to the user when a package is installed, or when
        certain version upgrade occur.

        :param package:
            The name of the package the message is for

        :param package_dir:
            The full filesystem path to the package directory

        :param is_upgrade:
            If the install was actually an upgrade

        :param old_version:
            The string version of the package before the upgrade occurred
        """

        messages_file = os.path.join(package_dir, 'messages.json')
        if not os.path.exists(messages_file):
            return

        messages_fp = open_compat(messages_file, 'r')
        try:
            message_info = json.loads(read_compat(messages_fp))
        except (ValueError):
            console_write(u'Error parsing messages.json for %s' % package, True)
            return
        messages_fp.close()

        output = ''
        if not is_upgrade and message_info.get('install'):
            install_messages = os.path.join(package_dir,
                message_info.get('install'))
            message = '\n\n%s:\n%s\n\n  ' % (package,
                        ('-' * len(package)))
            with open_compat(install_messages, 'r') as f:
                message += read_compat(f).replace('\n', '\n  ')
            output += message + '\n'

        elif is_upgrade and old_version:
            upgrade_messages = list(set(message_info.keys()) -
                set(['install']))
            upgrade_messages = sorted(upgrade_messages,
                cmp=self.compare_versions, reverse=True)
            for version in upgrade_messages:
                if self.compare_versions(old_version, version) >= 0:
                    break
                if not output:
                    message = '\n\n%s:\n%s\n' % (package,
                        ('-' * len(package)))
                    output += message
                upgrade_messages = os.path.join(package_dir,
                    message_info.get(version))
                message = '\n  '
                with open_compat(upgrade_messages, 'r') as f:
                    message += read_compat(f).replace('\n', '\n  ')
                output += message + '\n'

        if not output:
            return

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

            def write(string):
                edit = view.begin_edit()
                view.insert(edit, view.size(), string)
                view.end_edit(edit)

            if not view.size():
                view.settings().set("word_wrap", True)
                write('Package Control Messages\n' +
                    '========================')

            write(output)
        sublime.set_timeout(print_to_panel, 1)

    def remove_package(self, package_name):
        """
        Deletes a package

        The deletion process consists of:

        1. Deleting the directory (or marking it for deletion if deletion fails)
        2. Submitting usage info
        3. Removing the package from the list of installed packages

        :param package_name:
            The package to delete

        :return: bool if the package was successfully deleted
        """

        installed_packages = self.list_packages()

        if package_name not in installed_packages:
            show_error(u'The package specified, %s, is not installed' % package_name)
            return False

        os.chdir(sublime.packages_path())

        # Give Sublime Text some time to ignore the package
        time.sleep(1)

        package_filename = package_name + '.sublime-package'
        package_path = os.path.join(sublime.installed_packages_path(),
            package_filename)
        installed_package_path = os.path.join(os.path.dirname(
            sublime.packages_path()), 'Installed Packages', package_filename)
        pristine_package_path = os.path.join(os.path.dirname(
            sublime.packages_path()), 'Pristine Packages', package_filename)
        package_dir = self.get_package_dir(package_name)

        version = self.get_metadata(package_name).get('version')

        try:
            if os.path.exists(package_path):
                os.remove(package_path)
        except (OSError, IOError) as e:
            show_error(u'An error occurred while trying to remove the package file for %s.\n\n%s' % (
                package_name, unicode_from_os(e)))
            return False

        try:
            if os.path.exists(installed_package_path):
                os.remove(installed_package_path)
        except (OSError, IOError) as e:
            show_error(u'An error occurred while trying to remove the installed package file for %s.\n\n%s' % (
                package_name, unicode_from_os(e)))
            return False

        try:
            if os.path.exists(pristine_package_path):
                os.remove(pristine_package_path)
        except (OSError, IOError) as e:
            show_error(u'An error occurred while trying to remove the pristine package file for %s.\n\n%s' % (
                package_name, unicode_from_os(e)))
            return False

        # We don't delete the actual package dir immediately due to a bug
        # in sublime_plugin.py
        can_delete_dir = True
        if not clear_directory(package_dir):
            # If there is an error deleting now, we will mark it for
            # cleanup the next time Sublime Text starts
            open_compat(os.path.join(package_dir, 'package-control.cleanup'),
                'w').close()
            can_delete_dir = False

        params = {
            'package': package_name,
            'operation': 'remove',
            'version': version
        }
        self.record_usage(params)

        # Remove the package from the installed packages list
        def clear_package():
            settings = sublime.load_settings('Package Control.sublime-settings')
            installed_packages = settings.get('installed_packages', [])
            if not installed_packages:
                installed_packages = []
            installed_packages.remove(package_name)
            settings.set('installed_packages', installed_packages)
            sublime.save_settings('Package Control.sublime-settings')
        sublime.set_timeout(clear_package, 1)

        if can_delete_dir:
            os.rmdir(package_dir)

        return True

    def record_usage(self, params):
        """
        Submits install, upgrade and delete actions to a usage server

        The usage information is currently displayed on the Package Control
        community package list at http://wbond.net/sublime_packages/community

        :param params:
            A dict of the information to submit
        """

        if not self.settings.get('submit_usage'):
            return
        params['package_control_version'] = \
            self.get_metadata('Package Control').get('version')
        params['sublime_platform'] = self.settings.get('platform')
        params['sublime_version'] = self.settings.get('version')
        url = self.settings.get('submit_url') + '?' + urlencode(params)

        result = self.download_url(url, 'Error submitting usage information.')
        if result == False:
            return

        try:
            result = json.loads(result.decode('utf-8'))
            if result['result'] != 'success':
                raise ValueError()
        except (ValueError):
            console_write(u'Error submitting usage information for %s' % params['package'], True)
