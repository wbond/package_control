# coding=utf-8
import sublime
import sublime_plugin
import os
import sys
import subprocess
import zipfile
import urllib2
import hashlib
import json
import fnmatch
import re
import threading
import datetime
import time
import shutil
import _strptime

try:
    import ssl
except (ImportError):
    pass


class ChannelProvider():
    def __init__(self, channel, package_manager):
        self.channel_info = None
        self.channel = channel
        self.package_manager = package_manager

    def match_url(self, url):
        return True

    def fetch_channel(self):
        channel_json = self.package_manager.download_url(self.channel,
            'Error downloading channel.')
        if channel_json == False:
            self.channel_info = False
            return
        try:
            channel_info = json.loads(channel_json)
        except (ValueError):
            sublime.error_message(__name__ + ': Error parsing JSON from ' +
                ' channel ' + self.channel + '.')
            self.channel_info = False
            return
        self.channel_info = channel_info

    def get_name_map(self):
        if self.channel_info == None:
            self.fetch_channel()
        if self.channel_info == False:
            return False
        return self.channel_info['package_name_map']

    def get_repositories(self):
        if self.channel_info == None:
            self.fetch_channel()
        if self.channel_info == False:
            return False
        return self.channel_info['repositories']


_channel_providers = [ChannelProvider]


class PackageProvider():
    def match_url(self, url):
        return True

    def get_packages(self, repo, package_manager):
        repository_json = package_manager.download_url(repo,
            'Error downloading repository.')
        if repository_json == False:
            return False
        try:
            repo_info = json.loads(repository_json)
        except (ValueError):
            sublime.error_message(__name__ + ': Error parsing JSON from ' +
                ' repository ' + repo + '.')
            return False

        identifiers = [sublime.platform() + '-' + sublime.arch(),
            sublime.platform(), '*']
        output = {}
        for package in repo_info['packages']:
            for id in identifiers:
                if not id in package['platforms']:
                    continue

                downloads = []
                for download in package['platforms'][id]:
                    downloads.append(download)

                info = {
                    'name': package['name'],
                    'description': package.get('description'),
                    'url': package.get('url', repo),
                    'author': package.get('author'),
                    'downloads': downloads
                }

                output[package['name']] = info
                break
        return output


class GitHubPackageProvider():
    def match_url(self, url):
        return re.search('^https?://github.com/[^/]+/[^/]+$', url) != None

    def get_packages(self, repo, package_manager):
        api_url = re.sub('^https?://github.com/',
            'https://api.github.com/repos/', repo)
        repo_json = package_manager.download_url(api_url,
            'Error downloading repository.')
        if repo_json == False:
            return False
        try:
            repo_info = json.loads(repo_json)
        except (ValueError):
            sublime.error_message(__name__ + ': Error parsing JSON from ' +
                ' repository ' + repo + '.')
            return False

        commit_date = repo_info['pushed_at']
        timestamp = datetime.datetime.strptime(commit_date[0:19],
            '%Y-%m-%dT%H:%M:%S')
        utc_timestamp = timestamp.strftime(
            '%Y.%m.%d.%H.%M.%S')

        homepage = repo_info['homepage']
        if not homepage:
            homepage = repo_info['html_url']
        package = {
            'name': repo_info['name'],
            'description': repo_info['description'],
            'url': homepage,
            'author': repo_info['owner']['login'],
            'downloads': [
                {
                    'version': utc_timestamp,
                    'url': 'https://nodeload.github.com/' + \
                            repo_info['owner']['login'] + '/' + \
                            repo_info['name'] + '/zipball/master'
                }
            ]
        }
        return {package['name']: package}


class GitHubUserProvider():
    def match_url(self, url):
        return re.search('^https?://github.com/[^/]+$', url) != None

    def get_packages(self, url, package_manager):
        api_url = re.sub('^https?://github.com/',
            'https://api.github.com/users/', url) + '/repos'
        repo_json = package_manager.download_url(api_url,
            'Error downloading repository.')
        if repo_json == False:
            return False
        try:
            repo_info = json.loads(repo_json)
        except (ValueError):
            sublime.error_message(__name__ + ': Error parsing JSON from ' +
                ' repository ' + repo + '.')
            return False

        packages = {}
        for package_info in repo_info:
            commit_date = package_info['pushed_at']
            timestamp = datetime.datetime.strptime(commit_date[0:19],
                '%Y-%m-%dT%H:%M:%S')
            utc_timestamp = timestamp.strftime(
                '%Y.%m.%d.%H.%M.%S')

            homepage = package_info['homepage']
            if not homepage:
                homepage = package_info['html_url']
            package = {
                'name': package_info['name'],
                'description': package_info['description'],
                'url': homepage,
                'author': package_info['owner']['login'],
                'downloads': [
                    {
                        'version': utc_timestamp,
                        'url': 'https://nodeload.github.com/' + \
                            package_info['owner']['login'] + '/' + \
                            package_info['name'] + '/zipball/master'
                    }
                ]
            }
            packages[package['name']] = package
        return packages


class BitBucketPackageProvider():
    def match_url(self, url):
        return re.search('^https?://bitbucket.org', url) != None

    def get_packages(self, repo, package_manager):
        api_url = re.sub('^https?://bitbucket.org/',
            'https://api.bitbucket.org/1.0/repositories/', repo)
        repo_json = package_manager.download_url(api_url,
            'Error downloading repository.')
        if repo_json == False:
            return False
        try:
            repo_info = json.loads(repo_json)
        except (ValueError):
            sublime.error_message(__name__ + ': Error parsing JSON from ' +
                ' repository ' + repo + '.')
            return False

        changeset_json = package_manager.download_url(api_url + \
            '/changesets/?limit=1', 'Error downloading repository.')
        if changeset_json == False:
            return False
        try:
            last_commit = json.loads(changeset_json)
        except (ValueError):
            sublime.error_message(__name__ + ': Error parsing JSON from ' +
                ' repository ' + repo + '.')
            return False
        commit_date = last_commit['changesets'][0]['timestamp']
        timestamp = datetime.datetime.strptime(commit_date[0:19],
            '%Y-%m-%d %H:%M:%S')
        utc_timestamp = timestamp.strftime(
            '%Y.%m.%d.%H.%M.%S')

        homepage = repo_info['website']
        if not homepage:
            homepage = repo
        package = {
            'name': repo_info['slug'],
            'description': repo_info['description'],
            'url': homepage,
            'author': repo_info['owner'],
            'downloads': [
                {
                    'version': utc_timestamp,
                    'url': repo + '/get/' + \
                        last_commit['changesets'][0]['node'] + '.zip'
                }
            ]
        }
        return {package['name']: package}


_package_providers = [BitBucketPackageProvider, GitHubPackageProvider,
    GitHubUserProvider, PackageProvider]


class BinaryNotFoundError(Exception):
    pass


class NonCleanExitError(Exception):
    def __init__(self, returncode):
        self.returncode = returncode

    def __str__(self):
        return repr(self.returncode)


class CliDownloader():
    def find_binary(self, name):
        dirs = ['/usr/local/sbin', '/usr/local/bin', '/usr/sbin', '/usr/bin',
            '/sbin', '/bin']
        for dir in dirs:
            path = os.path.join(dir, name)
            if os.path.exists(path):
                return path

        raise BinaryNotFoundError('The binary ' + name + ' could not be ' + \
            'located')

    def execute(self, args):
        proc = subprocess.Popen(args, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        output = proc.stdout.read()
        returncode = proc.wait()
        if returncode != 0:
            raise NonCleanExitError(returncode)
        return output



class UrlLib2Downloader():
    def download(self, url, error_message, timeout):
        try:
            http_file = urllib2.urlopen(url, None, timeout)
            return http_file.read()

        except (urllib2.HTTPError) as (e):
            sublime.error_message(__name__ + ': ' + error_message +
                ' HTTP error ' + str(e.code) + ' downloading ' +
                url + '.')
        except (urllib2.URLError) as (e):
            sublime.error_message(__name__ + ': ' + error_message +
                ' URL error ' + str(e.reason) + ' downloading ' +
                url + '.')
        return False


class WgetDownloader(CliDownloader):
    def __init__(self):
        self.binary = self.find_binary('wget')

    def download(self, url, error_message, timeout):
        command = [self.binary, '--timeout', str(int(timeout)), '-o',
            '/dev/null', '-O', '-', url]

        try:
            return self.execute(command)
        except (NonCleanExitError) as (e):
            if e.returncode == 8:
                error_string = 'HTTP error 404'
            elif e.returncode == 4:
                error_string = 'URL error host not found'
            else:
                error_string = 'unknown connection error'

            sublime.error_message(__name__ + ': ' + error_message +
                ' ' + error_string + ' downloading ' +
                url + '.')
        return False


class CurlDownloader(CliDownloader):
    def __init__(self):
        self.binary = self.find_binary('curl')

    def download(self, url, error_message, timeout):
        curl = self.find_binary('curl')
        if not curl:
            return False
        command = [curl, '-f', '--connect-timeout', str(int(timeout)), '-s',
            url]

        try:
            return self.execute(command)
        except (NonCleanExitError) as (e):
            if e.returncode == 22:
                error_string = 'HTTP error 404'
            elif e.returncode == 6:
                error_string = 'URL error host not found'
            else:
                error_string = 'unknown connection error'

            sublime.error_message(__name__ + ': ' + error_message +
                ' ' + error_string + ' downloading ' +
                url + '.')
        return False

_channel_repository_cache = {}

class RepositoryDownloader(threading.Thread):
    def __init__(self, package_manager, name_map, repo):
        self.package_manager = package_manager
        self.repo = repo
        self.packages = {}
        self.name_map = name_map
        threading.Thread.__init__(self)

    def run(self):
        for provider_class in _package_providers:
            provider = provider_class()
            if provider.match_url(self.repo):
                break
        packages = provider.get_packages(self.repo, self.package_manager)
        if not packages:
            self.packages = {}
            return

        mapped_packages = {}
        for package in packages.keys():
            mapped_package = self.name_map.get(package, package)
            mapped_packages[mapped_package] = packages[package]
            mapped_packages[mapped_package]['name'] = mapped_package
        packages = mapped_packages

        self.packages = packages


class PackageManager():
    def __init__(self):
        # Here we manually copy the settings since sublime doesn't like
        # code accessing settings from threads
        self.settings = {}
        settings = sublime.load_settings(__name__ + '.sublime-settings')
        for setting in ['timeout', 'repositories', 'repository_channels',
                'package_name_map', 'dirs_to_ignore', 'files_to_ignore',
                'package_destination', 'cache_length', 'auto_upgrade',
                'files_to_ignore_binary']:
            if settings.get(setting) == None:
                continue
            self.settings[setting] = settings.get(setting)

    def compare_versions(self, version1, version2):
        def normalize(v):
            return [int(x) for x in re.sub(r'(\.0+)*$','', v).split(".")]
        return cmp(normalize(version1), normalize(version2))

    def download_url(self, url, error_message):
        has_ssl = 'ssl' in sys.modules
        is_ssl = re.search('^https://', url) != None

        if (is_ssl and has_ssl) or not is_ssl:
            downloader = UrlLib2Downloader()
        else:
            for downloader_class in [CurlDownloader, WgetDownloader]:
                try:
                    downloader = downloader_class()
                    break
                except (BinaryNotFoundError):
                    pass

        if not downloader:
            sublime.error_message(__name__ + ': Unable to download ' +
                url + ' due to no ssl module available and no capable ' +
                'program found. Please install curl or wget.')
            return False

        timeout = self.settings.get('timeout', 3)
        return downloader.download(url.replace(' ', '%20'), error_message, timeout)

    def get_metadata(self, package):
        metadata_filename = os.path.join(self.get_package_dir(package),
            'package-metadata.json')
        if os.path.exists(metadata_filename):
            with open(metadata_filename) as f:
                try:
                    return json.load(f)
                except (ValueError):
                    return {}
        return {}

    def list_repositories(self):
        repositories = self.settings.get('repositories')
        repository_channels = self.settings.get('repository_channels')
        for channel in repository_channels:
            channel_repositories = None

            cache_key = channel + '.repositories'
            repositories_cache = _channel_repository_cache.get(cache_key)
            if repositories_cache and repositories_cache.get('time') > \
                    time.time():
                channel_repositories = repositories_cache.get('data')

            if not channel_repositories:
                for provider_class in _channel_providers:
                    provider = provider_class(channel, self)
                    if provider.match_url(channel):
                        break
                channel_repositories = provider.get_repositories()
                if channel_repositories == False:
                    continue
                _channel_repository_cache[cache_key] = {
                    'time': time.time() + self.settings.get('cache_length',
                        300),
                    'data': channel_repositories
                }
                # Have the local name map override the one from the channel
                name_map = provider.get_name_map()
                name_map.update(self.settings['package_name_map'])
                self.settings['package_name_map'] = name_map

            repositories.extend(channel_repositories)
        return repositories

    def list_available_packages(self):
        repositories = self.list_repositories()
        packages = {}
        downloaders = []

        # Repositories are run in reverse order so that the ones first
        # on the list will overwrite those last on the list
        for repo in repositories[::-1]:
            repository_packages = None

            cache_key = repo + '.packages'
            packages_cache = _channel_repository_cache.get(cache_key)
            if packages_cache and packages_cache.get('time') > \
                    time.time():
                repository_packages = packages_cache.get('data')
                packages.update(repository_packages)

            if not repository_packages:
                downloader = RepositoryDownloader(self,
                    self.settings.get('package_name_map', {}), repo)
                downloader.start()
                downloaders.append(downloader)

        # Wait until all of the downloaders have completed
        while True:
            is_alive = False
            for downloader in downloaders:
                is_alive = downloader.is_alive() or is_alive
            if not is_alive:
                break
            time.sleep(0.01)

        for downloader in downloaders:
            repository_packages = downloader.packages
            if not repository_packages:
                continue
            cache_key = downloader.repo + '.packages'
            _channel_repository_cache[cache_key] = {
                'time': time.time() + self.settings.get('cache_length', 300),
                'data': repository_packages
            }
            packages.update(repository_packages)

        return packages

    def list_packages(self):
        package_names = os.listdir(sublime.packages_path())
        package_names = [path for path in package_names if
            os.path.isdir(os.path.join(sublime.packages_path(), path))]
        packages = list(set(package_names) - set(self.list_default_packages()))
        packages.sort()
        return packages

    def list_all_packages(self):
        packages = os.listdir(sublime.packages_path())
        packages.sort()
        return packages

    def list_default_packages(self):
        files = os.listdir(os.path.join(os.path.dirname(
            sublime.packages_path()), 'Pristine Packages'))
        files = list(set(files) - set(os.listdir(
            sublime.installed_packages_path())))
        packages = [file.replace('.sublime-package', '') for file in files]
        packages.sort()
        return packages

    def get_package_dir(self, package):
        return os.path.join(sublime.packages_path(), package)

    def get_mapped_name(self, package):
        return self.settings.get('package_name_map', {}).get(package, package)

    def create_package(self, package_name, package_destination,
            binary_package=False):
        package_dir = self.get_package_dir(package_name) + '/'

        if not os.path.exists(package_dir):
            sublime.error_message(__name__ + ': The folder for the ' +
                'package name specified, %s, does not exist in %s' %
                (package_name, sublime.packages_path()))
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
        except (OSError, IOError) as (exception):
            sublime.error_message(__name__ + ': An error occurred ' +
                'creating the package file %s in %s. %s' % (package_filename,
                package_destination, str(exception)))
            return False

        dirs_to_ignore = self.settings.get('dirs_to_ignore', [])
        if not binary_package:
            files_to_ignore = self.settings.get('files_to_ignore', [])
        else:
            files_to_ignore = self.settings.get('files_to_ignore_binary', [])

        package_dir_regex = re.compile('^' + re.escape(package_dir))
        for root, dirs, files in os.walk(package_dir):
            [dirs.remove(dir) for dir in dirs if dir in dirs_to_ignore]
            paths = dirs
            paths.extend(files)
            for path in paths:
                if any(fnmatch.fnmatch(path, pattern) for pattern in
                        files_to_ignore):
                    continue
                full_path = os.path.join(root, path)
                relative_path = re.sub(package_dir_regex, '', full_path)
                if os.path.isdir(full_path):
                    continue
                package_file.write(full_path, relative_path)

        init_script = os.path.join(package_dir, '__init__.py')
        if binary_package and os.path.exists(init_script):
            package_file.write(init_script, re.sub(package_dir_regex, '',
                init_script))
        package_file.close()

        return True

    def install_package(self, package_name):
        installed_packages = self.list_packages()
        packages = self.list_available_packages()

        if package_name not in packages.keys():
            sublime.error_message(__name__ + ': The package specified,' +
                ' %s, is not available.' % (package_name,))
            return False

        download = packages[package_name]['downloads'][0]
        url = download['url']

        package_filename = package_name + \
            '.sublime-package'
        package_path = os.path.join(sublime.installed_packages_path(),
            package_filename)

        package_bytes = self.download_url(url, 'Error downloading package.')
        if package_bytes == False:
            return False
        with open(package_path, "wb") as package_file:
            package_file.write(package_bytes)

        package_dir = self.get_package_dir(package_name)
        if not os.path.exists(package_dir):
            os.mkdir(package_dir)

        # Here we clean out the directory to preven issues with old files
        # however don't just recursively delete the whole package dir since
        # that will fail on Windows if a user has explorer open to it
        try:
            for path in os.listdir(package_dir):
                full_path = os.path.join(package_dir, path)
                if os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                else:
                    os.remove(full_path)
        except (OSError, IOError) as (exception):
            sublime.error_message(__name__ + ': An error occurred while' +
                ' trying to remove the package directory for %s. %s' %
                (package_name, str(exception)))
            return False

        package_zip = zipfile.ZipFile(package_path, 'r')
        for path in package_zip.namelist():
            if path[0] == '/' or path.find('..') != -1:
                sublime.error_message(__name__ + ': The package ' +
                    'specified, %s, contains files outside of the package ' +
                    'dir and cannot be safely installed.' % (package_name,))
                return False

        os.chdir(package_dir)

        # Here we don’t use .extractall() since it was having issues on OS X
        for path in package_zip.namelist():
            if path.endswith('/'):
                os.makedirs(os.path.join(package_dir, path))
            else:
                package_zip.extract(path)
        package_zip.close()

        # If the zip contained a single directory, pop everything up a level
        # and repackage the zip file
        extracted_paths = os.listdir(package_dir)
        extracted_paths = list(set(extracted_paths) - set(['.DS_Store']))
        if len(extracted_paths) == 1 and os.path.isdir(extracted_paths[0]):
            single_dir = os.path.join(package_dir, extracted_paths[0])
            for path in os.listdir(single_dir):
                shutil.move(os.path.join(single_dir, path), package_dir)
            os.rmdir(single_dir)
            self.create_package(package_name,
                sublime.installed_packages_path())

        package_metadata_file = os.path.join(package_dir,
            'package-metadata.json')
        with open(package_metadata_file, 'w') as f:
            metadata = {
                "version": packages[package_name]['downloads'][0]['version'],
                "url": packages[package_name]['url'],
                "description": packages[package_name]['description']
            }
            json.dump(metadata, f)

        # Here we delete the package file from the installed packages directory
        # since we don't want to accidentally overwrite user changes
        os.remove(package_path)

        os.chdir(sublime.packages_path())
        return True


    def remove_package(self, package_name):
        installed_packages = self.list_packages()

        if package_name not in installed_packages:
            sublime.error_message(__name__ + ': The package specified,' +
                ' %s, is not installed.' % (package_name,))
            return False

        package_filename = package_name + '.sublime-package'
        package_path = os.path.join(sublime.installed_packages_path(),
            package_filename)
        pristine_package_path = os.path.join(os.path.dirname(
            sublime.packages_path()), 'Pristine Packages', package_filename)
        package_dir = self.get_package_dir(package_name)

        try:
            if os.path.exists(package_path):
                os.remove(package_path)
        except (OSError, IOError) as (exception):
            sublime.error_message(__name__ + ': An error occurred while' +
                ' trying to remove the package file for %s. %s' %
                (package_name, str(exception)))
            return False

        try:
            if os.path.exists(pristine_package_path):
                os.remove(pristine_package_path)
        except (OSError, IOError) as (exception):
            sublime.error_message(__name__ + ': An error occurred while' +
                ' trying to remove the pristine package file for %s. %s' %
                (package_name, str(exception)))
            return False

        try:
            # We don't delete the actual package dir immediately due to a bug
            # in sublime_plugin.py
            for path in os.listdir(package_dir):
                full_path = os.path.join(package_dir, path)
                if os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                else:
                    os.remove(full_path)
        except (OSError, IOError) as (exception):
            sublime.error_message(__name__ + ': An error occurred while' +
                ' trying to remove the package directory for %s. %s' %
                (package_name, str(exception)))
            return False

        # Here we clean up the package dir
        def remove_package_dir():
            os.chdir(sublime.packages_path())
            os.rmdir(package_dir)
        sublime.set_timeout(remove_package_dir, 2000)

        return True


class PackageCreator():
    def show_panel(self):
        self.manager = PackageManager()
        self.packages = self.manager.list_packages()
        if not self.packages:
            sublime.error_message(__name__ + ': There are no packages ' +
                'available to be packaged.')
            return
        self.window.show_quick_panel(self.packages, self.on_done)

    def get_package_destination(self):
        destination = self.manager.settings.get('package_destination')

        # We check destination via an if statement instead of using
        # the dict.get() method since the key may be set, but to a blank value
        if not destination:
            destination = os.path.join(os.path.expanduser('~'),
                'Desktop')

        return destination

    def on_done(self):
        print 'Hi!'
        pass


class CreatePackageCommand(sublime_plugin.WindowCommand, PackageCreator):
    def run(self):
        self.show_panel()

    def on_done(self, picked):
        if picked == -1:
            return
        package_name = self.packages[picked]
        package_destination = self.get_package_destination()

        if self.manager.create_package(package_name, package_destination):
            self.window.run_command('open_dir', {"dir":
                package_destination, "file": package_name +
                '.sublime-package'})


class CreateBinaryPackageCommand(sublime_plugin.WindowCommand, PackageCreator):
    def run(self):
        self.show_panel()

    def on_done(self, picked):
        if picked == -1:
            return
        package_name = self.packages[picked]
        package_destination = self.get_package_destination()

        if self.manager.create_package(package_name, package_destination,
                binary_package=True):
            self.window.run_command('open_dir', {"dir":
                package_destination, "file": package_name +
                '.sublime-package'})


class PackageInstaller():
    def __init__(self):
        self.manager = PackageManager()

    def make_package_list(self, ignore_actions=[]):
        packages = self.manager.list_available_packages()
        installed_packages = self.manager.list_packages()

        package_list = []
        for package in sorted(packages.iterkeys()):
            package_entry = [package]
            info = packages[package]
            download = info['downloads'][0]

            if package in installed_packages:
                installed = True
                metadata = self.manager.get_metadata(package)
                if metadata.get('version'):
                    installed_version = metadata['version']
                else:
                    installed_version = None
            else:
                installed = False

            installed_version_name = 'v' + installed_version if \
                installed and installed_version else 'unknown version'
            new_version = 'v' + download['version']

            if installed:
                if not installed_version:
                    action = 'overwrite'
                    extra = ' %s with %s' % (installed_version_name,
                        new_version)
                else:
                    res = self.manager.compare_versions(
                        installed_version, download['version'])
                    if res < 0:
                        action = 'upgrade'
                        extra = ' to %s from %s' % (new_version,
                            installed_version_name)
                    elif res > 0:
                        action = 'downgrade'
                        extra = ' to %s from %s' % (new_version,
                            installed_version_name)
                    else:
                        action = 'reinstall'
                        extra = ' %s' % new_version
            else:
                action = 'install'
                extra = ' %s' % new_version

            if action in ignore_actions:
                continue

            package_entry.append(info.get('description', 'No description ' + \
                'provided'))
            package_entry.append(action + extra + '; ' +
                re.sub('^https?://', '', info['url']))
            package_list.append(package_entry)
        return package_list

    def on_done(self, picked):
        if picked == -1:
            return
        package_name = self.package_list[picked][0]
        self.install_package(package_name)
        sublime.status_message('Package ' + package_name + ' successfully ' +
            self.completion_type)

    def install_package(self, name):
        self.manager.install_package(name)


class InstallPackageCommand(sublime_plugin.WindowCommand):
    def run(self):
        sublime.status_message(u'Loading repositories, please wait…')
        InstallPackageThread(self.window).start()

    def on_done(self, picked):
        return


class InstallPackageThread(threading.Thread, PackageInstaller):
    def __init__(self, window):
        self.window = window
        self.completion_type = 'installed'
        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        self.package_list = self.make_package_list(['upgrade', 'downgrade',
            'reinstall'])
        def show_quick_panel():
            if not self.package_list:
                sublime.error_message(__name__ + ': There are no packages ' +
                    'available for installation.')
                return
            self.window.show_quick_panel(self.package_list, self.on_done)
        sublime.set_timeout(show_quick_panel, 0)


class DiscoverPackagesCommand(sublime_plugin.WindowCommand):
    def run(self):
        sublime.status_message(u'Loading repositories, please wait…')
        DiscoverPackagesThread(self.window).start()

    def on_done(self, picked):
        return


class DiscoverPackagesThread(threading.Thread, PackageInstaller):
    def __init__(self, window):
        self.window = window
        self.completion_type = 'installed'
        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        self.package_list = self.make_package_list()
        def show_quick_panel():
            if not self.package_list:
                sublime.error_message(__name__ + ': There are no packages ' +
                    'available for discovery.')
                return
            self.window.show_quick_panel(self.package_list, self.on_done)
        sublime.set_timeout(show_quick_panel, 0)

    def on_done(self, picked):
        if picked == -1:
            return
        package_name = self.package_list[picked][0]
        packages = self.manager.list_available_packages()
        def open_url():
            sublime.active_window().run_command('open_url',
                {"url": packages.get(package_name).get('url')})
        sublime.set_timeout(open_url, 0)


class UpgradePackageCommand(sublime_plugin.WindowCommand):
    def run(self):
        sublime.status_message(u'Loading repositories, please wait…')
        UpgradePackageThread(self.window).start()


class UpgradePackageThread(threading.Thread, PackageInstaller):
    def __init__(self, window):
        self.window = window
        self.completion_type = 'upgraded'
        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        self.package_list = self.make_package_list(['install'])
        def show_quick_panel():
            if not self.package_list:
                sublime.error_message(__name__ + ': There are no packages ' +
                    'ready for upgrade.')
                return
            self.window.show_quick_panel(self.package_list, self.on_done)
        sublime.set_timeout(show_quick_panel, 0)


class ExistingPackagesCommand():
    def __init__(self):
        self.manager = PackageManager()

    def make_package_list(self, action=''):
        packages = self.manager.list_packages()

        if action:
            action += ' '

        package_list = []
        for package in sorted(packages):
            package_entry = [package]
            metadata = self.manager.get_metadata(package)

            package_entry.append(metadata.get('description',
                'No description provided'))

            version = metadata.get('version')
            installed_version = 'v' + version if version else 'unknown version'

            url = metadata.get('url')
            if url:
                url = '; ' + re.sub('^https?://', '', url)
            else:
                url = ''

            package_entry.append(action + installed_version + url)
            package_list.append(package_entry)

        return package_list


class ListPackagesCommand(sublime_plugin.WindowCommand):
    def run(self):
        ListPackagesThread(self.window).start()


class ListPackagesThread(threading.Thread, ExistingPackagesCommand):
    def __init__(self, window):
        self.window = window
        threading.Thread.__init__(self)
        ExistingPackagesCommand.__init__(self)

    def run(self):
        self.package_list = self.make_package_list()

        def show_quick_panel():
            if not self.package_list:
                sublime.error_message(__name__ + ': There are no packages ' +
                    'to list.')
                return
            self.window.show_quick_panel(self.package_list, self.on_done)
        sublime.set_timeout(show_quick_panel, 0)

    def on_done(self, picked):
        if picked == -1:
            return
        package_name = self.package_list[picked][0]
        def open_dir():
            self.window.run_command('open_dir',
                {"dir": os.path.join(sublime.packages_path(), package_name)})
        sublime.set_timeout(open_dir, 0)


class RemovePackageCommand(sublime_plugin.WindowCommand,
        ExistingPackagesCommand):
    def __init__(self, window):
        self.window = window
        ExistingPackagesCommand.__init__(self)

    def run(self):
        self.package_list = self.make_package_list('remove')
        if not self.package_list:
            sublime.error_message(__name__ + ': There are no packages ' +
                'that can be removed.')
            return
        self.window.show_quick_panel(self.package_list, self.on_done)

    def on_done(self, picked):
        if picked == -1:
            return
        package = self.package_list[picked][0]
        self.manager.remove_package(package)
        sublime.status_message('Package ' + package + ' successfully removed')


class AddRepositoryChannelCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.show_input_panel('Repository Channel URL', '',
            self.on_done, self.on_change, self.on_cancel)

    def on_done(self, input):
        settings = sublime.load_settings(__name__ + '.sublime-settings')
        repository_channels = settings.get('repository_channels', [])
        if not repository_channels:
            repository_channels = []
        repository_channels.append(input)
        settings.set('repository_channels', repository_channels)
        sublime.save_settings(__name__ + '.sublime-settings')
        sublime.status_message('Repository channel ' + input + ' successfully added')

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass


class AddRepositoryCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.show_input_panel('Repository URL', '', self.on_done,
            self.on_change, self.on_cancel)

    def on_done(self, input):
        settings = sublime.load_settings(__name__ + '.sublime-settings')
        repositories = settings.get('repositories', [])
        if not repositories:
            repositories = []
        repositories.append(input)
        settings.set('repositories', repositories)
        sublime.save_settings(__name__ + '.sublime-settings')
        sublime.status_message('Repository ' + input + ' successfully added')

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass


class DisablePackageCommand(sublime_plugin.WindowCommand):
    def run(self):
        manager = PackageManager()
        packages = manager.list_all_packages()
        self.settings = sublime.load_settings('Global.sublime-settings')
        disabled_packages = self.settings.get('ignored_packages')
        if not disabled_packages:
            disabled_packages = []
        self.package_list = list(set(packages) - set(disabled_packages))
        self.package_list.sort()
        if not self.package_list:
            sublime.error_message(__name__ + ': There are no enabled ' +
            'packages to disable.')
            return
        self.window.show_quick_panel(self.package_list, self.on_done)

    def on_done(self, picked):
        if picked == -1:
            return
        package = self.package_list[picked]
        ignored_packages = self.settings.get('ignored_packages')
        if not ignored_packages:
            ignored_packages = []
        ignored_packages.append(package)
        self.settings.set('ignored_packages', ignored_packages)
        sublime.save_settings('Global.sublime-settings')
        sublime.status_message('Package ' + package + ' successfully added ' +
            'to list of diabled packges - restarting Sublime Text may be '
            'required')


class EnablePackageCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.settings = sublime.load_settings('Global.sublime-settings')
        self.disabled_packages = self.settings.get('ignored_packages')
        self.disabled_packages.sort()
        if not self.disabled_packages:
            sublime.error_message(__name__ + ': There are no disabled ' +
            'packages to enable.')
            return
        self.window.show_quick_panel(self.disabled_packages, self.on_done)

    def on_done(self, picked):
        if picked == -1:
            return
        package = self.disabled_packages[picked]
        ignored = self.settings.get('ignored_packages')
        self.settings.set('ignored_packages',
            list(set(ignored) - set([package])))
        sublime.save_settings('Global.sublime-settings')
        sublime.status_message('Package ' + package + ' successfully removed ' +
            'from list of diabled packages - restarting Sublime Text may be '
            'required')


class AutomaticUpgrader(threading.Thread):
    def __init__(self):
        self.installer = PackageInstaller()
        self.auto_upgrade = PackageManager().settings.get('auto_upgrade')
        threading.Thread.__init__(self)

    def run(self):
        if self.auto_upgrade:
            packages = self.installer.make_package_list(['install', 'reinstall',
                'downgrade', 'overwrite'])
            if not packages:
                print __name__ + ': No updated packages'
                return

            print __name__ + ': Installing %s upgrades' % len(packages)
            for package in packages:
                self.installer.install_package(package[0])
                print __name__ + ': Upgraded %s to %s' % (package[0],
                    re.sub('^.*?(v[\d\.]+).*?$', '\\1', package[1]))

AutomaticUpgrader().start()