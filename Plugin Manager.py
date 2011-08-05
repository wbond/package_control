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
from fnmatch import fnmatch
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
    def match_url(self, url):
        return True

    def get_repositories(self, channel, plugin_manager):
        channel_json = plugin_manager.download_url(channel,
            'Error downloading channel.')
        if channel_json == False:
            return False
        try:
            channel_info = json.loads(channel_json)
        except (ValueError):
            sublime.error_message('Plugin Manager: Error parsing JSON from ' +
                ' channel ' + channel + '.')
            return False
        return channel_info['repositories']


_channel_providers = [ChannelProvider]


class PackageProvider():
    def match_url(self, url):
        return True

    def get_packages(self, repo, plugin_manager):
        repository_json = plugin_manager.download_url(repo,
            'Error downloading repository.')
        if repository_json == False:
            return False
        try:
            repo_info = json.loads(repository_json)
        except (ValueError):
            sublime.error_message('Plugin Manager: Error parsing JSON from ' +
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
                    'downloads': downloads
                }

                output[package['name']] = info
                break
        return output


class GitHubPackageProvider():
    def match_url(self, url):
        return re.search('^https?://github.com/[^/]+/[^/]+$', url) != None

    def get_packages(self, repo, plugin_manager):
        api_url = re.sub('^https?://github.com/',
            'https://api.github.com/repos/', repo)
        repo_json = plugin_manager.download_url(api_url,
            'Error downloading repository.')
        if repo_json == False:
            return False
        try:
            repo_info = json.loads(repo_json)
        except (ValueError):
            sublime.error_message('Plugin Manager: Error parsing JSON from ' +
                ' repository ' + repo + '.')
            return False

        commit_date = repo_info['pushed_at']
        timestamp = datetime.datetime.strptime(commit_date[0:19],
            '%Y-%m-%dT%H:%M:%S')
        utc_timestamp = timestamp.strftime(
            '%Y.%m.%d.%H.%M.%S')

        package = {
            'name': repo_info['name'],
            'description': repo_info['description'],
            'url': repo,
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

    def get_packages(self, url, plugin_manager):
        api_url = re.sub('^https?://github.com/',
            'https://api.github.com/users/', url) + '/repos'
        repo_json = plugin_manager.download_url(api_url,
            'Error downloading repository.')
        if repo_json == False:
            return False
        try:
            repo_info = json.loads(repo_json)
        except (ValueError):
            sublime.error_message('Plugin Manager: Error parsing JSON from ' +
                ' repository ' + repo + '.')
            return False

        packages = {}
        for package_info in repo_info:
            commit_date = package_info['pushed_at']
            timestamp = datetime.datetime.strptime(commit_date[0:19],
                '%Y-%m-%dT%H:%M:%S')
            utc_timestamp = timestamp.strftime(
                '%Y.%m.%d.%H.%M.%S')

            package = {
                'name': package_info['name'],
                'description': package_info['description'],
                'url': package_info['html_url'],
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

    def get_packages(self, repo, plugin_manager):
        api_url = re.sub('^https?://bitbucket.org/',
            'https://api.bitbucket.org/1.0/repositories/', repo)
        repo_json = plugin_manager.download_url(api_url,
            'Error downloading repository.')
        if repo_json == False:
            return False
        try:
            repo_info = json.loads(repo_json)
        except (ValueError):
            sublime.error_message('Plugin Manager: Error parsing JSON from ' +
                ' repository ' + repo + '.')
            return False

        changeset_json = plugin_manager.download_url(api_url + \
            '/changesets/?limit=1', 'Error downloading repository.')
        if changeset_json == False:
            return False
        try:
            last_commit = json.loads(changeset_json)
        except (ValueError):
            sublime.error_message('Plugin Manager: Error parsing JSON from ' +
                ' repository ' + repo + '.')
            return False
        commit_date = last_commit['changesets'][0]['timestamp']
        timestamp = datetime.strptime('%Y-%m-%d %H-%M-%S')
        utc_timestamp = timestamp.strftime(
            '%Y.%m.%d.%H.%M.%S')

        package = {
            'name': repo_info['name'],
            'description': repo_info['description'],
            'url': repo,
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
            sublime.error_message('Plugin Manager: ' + error_message +
                ' HTTP error ' + str(e.code) + ' downloading ' +
                url + '.')
        except (urllib2.URLError) as (e):
            sublime.error_message('Plugin Manager: ' + error_message +
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

            sublime.error_message('Plugin Manager: ' + error_message +
                ' ' + error_string + ' downloading ' +
                url + '.')


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

            sublime.error_message('Plugin Manager: ' + error_message +
                ' ' + error_string + ' downloading ' +
                url + '.')


class RepositoryDownloader(threading.Thread):
    def __init__(self, plugin_manager, installed_packages, name_map, repo):
        self.plugin_manager = plugin_manager
        self.installed_packages = installed_packages
        self.repo = repo
        self.packages = {}
        self.name_map = name_map
        threading.Thread.__init__(self)

    def run(self):
        for provider_class in _package_providers:
            provider = provider_class()
            if provider.match_url(self.repo):
                break
        packages = provider.get_packages(self.repo, self.plugin_manager)
        if not packages:
            self.packages = {}
            return

        mapped_packages = {}
        for package in packages.keys():
            mapped_package = self.name_map.get(package, package)
            mapped_packages[mapped_package] = packages[package]
            mapped_packages[mapped_package]['name'] = mapped_package
        packages = mapped_packages

        for package in packages.keys():
            if package in self.installed_packages:
                packages[package]['installed'] = True
                metadata = self.plugin_manager.get_metadata(package)
                if metadata.get('version'):
                    packages[package]['installed_version'] = \
                        metadata['version']
            else:
                packages[package]['installed'] = False

        self.packages = packages


class PluginManager():
    def __init__(self):
        # Here we manually copy the settings since sublime doesn't like
        # code accessing settings from threads
        self.settings = {}
        settings = sublime.load_settings('Plugin Manager.sublime-settings')
        for setting in ['timeout', 'repositories', 'repository_channels',
                'plugin_name_map', 'dirs_to_ignore', 'files_to_ignore']:
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
            sublime.error_message('Plugin Manager: Unable to download ' +
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
            for provider_class in _channel_providers:
                provider = provider_class()
                if provider.match_url(channel):
                    break
            channel_repositories = provider.get_repositories(channel, self)
            if channel_repositories == False:
                continue
            repositories.extend(channel_repositories)
        return repositories

    def list_available_packages(self):
        repositories = self.list_repositories()
        installed_packages = self.list_packages()
        packages = {}
        downloaders = []

        # Repositories are run in reverse order so that the ones first
        # on the list will overwrite those last on the list
        for repo in repositories[::-1]:
            downloader = RepositoryDownloader(self, installed_packages,
                self.settings.get('plugin_name_map', {}), repo)
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
            packages.update(repository_packages)

        return packages

    def list_packages(self):
        package_names = os.listdir(sublime.packages_path())
        package_names = [path for path in package_names if
            os.path.isdir(os.path.join(sublime.packages_path(), path))]
        packages = list(set(package_names) - set(self.list_default_packages()))
        packages.sort()
        return packages

    def list_default_packages(self):
        files = os.listdir(sublime.packages_path() + '/../Pristine Packages/')
        files = list(set(files) - set(os.listdir(
            sublime.installed_packages_path())))
        packages = [file.replace('.sublime-package', '') for file in files]
        packages.sort()
        return packages

    def get_package_dir(self, package):
        return os.path.join(sublime.packages_path(), package)

    def get_mapped_name(self, package):
        return self.settings.get('plugin_name_map', {}).get(package, package)

    def create_package(self, package_name):
        package_dir = self.get_package_dir(package_name) + '/'

        if not os.path.exists(package_dir):
            sublime.error_message('Plugin Manager: The folder for the ' +
                'package name specified, %s, does not exist in %s' %
                (package_name, sublime.packages_path()))
            return False

        package_filename = os.path.join(sublime.installed_packages_path(),
            package_name + '.sublime-package')

        if not os.path.exists(sublime.installed_packages_path()):
            os.mkdir(sublime.installed_packages_path())

        if os.path.exists(package_filename):
            os.remove(package_filename)

        package_file = zipfile.ZipFile(package_filename, "w",
            compression=zipfile.ZIP_DEFLATED)

        dirs_to_ignore = self.settings.get('dirs_to_ignore', [])
        files_to_ignore = self.settings.get('files_to_ignore', [])

        package_dir_regex = re.compile('^' + re.escape(package_dir))
        for root, dirs, files in os.walk(package_dir):
            [dirs.remove(dir) for dir in dirs if dir in dirs_to_ignore]
            paths = dirs
            paths.extend(files)
            for path in paths:
                if any(fnmatch(path, pattern) for pattern in files_to_ignore):
                    continue
                full_path = os.path.join(root, path)
                relative_path = re.sub(package_dir_regex, '', full_path)
                if os.path.isdir(full_path):
                    continue
                package_file.write(full_path, relative_path)
        package_file.close()
        return True

    def install_package(self, package_name):
        installed_packages = self.list_packages()
        packages = self.list_available_packages()

        if package_name not in packages.keys():
            sublime.error_message('Plugin Manager: The package specified,' +
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
        except (OSError, WindowsError) as (exception):
            sublime.error_message('Plugin Manager: An error occurred while' +
                ' trying to remove the package directory for %s. %s' %
                (package_name, str(exception)))
            return False

        package_zip = zipfile.ZipFile(package_path, 'r')
        for path in package_zip.namelist():
            if path[0] == '/' or path.find('..') != -1:
                sublime.error_message('Plugin Manager: The package ' +
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
            self.create_package(package_name)

        package_metadata_file = os.path.join(package_dir,
            'package-metadata.json')
        with open(package_metadata_file, 'w') as f:
            metadata = {
                "version": packages[package_name]['downloads'][0]['version'],
                "url": packages[package_name]['url'],
                "description": packages[package_name]['description']
            }
            json.dump(metadata, f)
        return True


    def remove_package(self, package_name):
        installed_packages = self.list_packages()

        if package_name not in installed_packages:
            sublime.error_message('Plugin Manager: The package specified,' +
                ' %s, is not installed.' % (package_name,))
            return False

        package_filename = package_name + '.sublime-package'
        package_path = os.path.join(sublime.installed_packages_path(),
            package_filename)
        package_dir = self.get_package_dir(package_name)

        try:
            if os.path.exists(package_path):
                os.remove(package_path)
        except (OSError) as (exception):
            sublime.error_message('Plugin Manager: An error occurred while' +
                ' trying to remove the package file for %s. %s' %
                (package_name, str(exception)))
            return False

        try:
            shutil.rmtree(package_dir)
        except (OSError) as (exception):
            sublime.error_message('Plugin Manager: An error occurred while' +
                ' trying to remove the package directory for %s. %s' %
                (package_name, str(exception)))
            return False

        return True


class CreatePackageCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.manager = PluginManager()
        self.packages = self.manager.list_packages()
        self.window.show_quick_panel(self.packages, self.on_done)

    def on_done(self, picked):
        if picked == -1:
            return
        package_name = self.packages[picked]
        if self.manager.create_package(package_name):
            self.window.run_command('open_dir', {"dir":
                sublime.installed_packages_path(), "file": package_name +
                '.sublime-package'})


class PluginInstaller():
    def __init__(self):
        self.manager = PluginManager()

    def make_package_list(self, ignore_actions=[]):
        packages = self.manager.list_available_packages()

        package_list = []
        for package in sorted(packages.iterkeys()):
            package_entry = [package]
            info = packages[package]
            download = info['downloads'][0]
            if info['installed']:
                if 'installed_version' not in info:
                    action = 'overwrite unknown'
                else:
                    res = self.manager.compare_versions(
                        info['installed_version'], download['version'])
                    if res < 0:
                        action = 'upgrade'
                    elif res > 0:
                        action = 'downgrade'
                    else:
                        action = 'reinstall'
            else:
                action = 'install'
            if action in ignore_actions:
                continue

            if action in ['upgrade', 'downgrade']:
                action += ' from v' + info['installed_version']
            if action == 'overwrite unknown':
                action += ' version'

            package_entry.append(info.get('description', 'No description ' + \
                'provided'))
            package_entry.append('v' + download['version'] + '; ' +
                re.sub('^https?://', '', info['url']) + '; action: ' + action)
            package_list.append(package_entry)
        return package_list

    def on_done(self, picked):
        if picked == -1:
            return
        package_name = self.package_list[picked][0]
        self.install_package(package_name)
        sublime.status_message('Plugin ' + package_name + ' successfully ' +
            self.completion_type)

    def install_package(self, name):
        self.manager.install_package(name)


class InstallPluginCommand(sublime_plugin.WindowCommand):
    def run(self):
        sublime.status_message(u'Loading repositories, please wait…')
        InstallPluginThread(self.window).start()

    def on_done(self, picked):
        return


class InstallPluginThread(threading.Thread, PluginInstaller):
    def __init__(self, window):
        self.window = window
        self.completion_type = 'installed'
        threading.Thread.__init__(self)
        PluginInstaller.__init__(self)

    def run(self):
        self.package_list = self.make_package_list(['upgrade', 'downgrade',
            'reinstall'])
        def show_quick_panel():
            self.window.show_quick_panel(self.package_list, self.on_done)
        sublime.set_timeout(show_quick_panel, 0)


class UpgradePluginCommand(sublime_plugin.WindowCommand):
    def run(self):
        sublime.status_message(u'Loading repositories, please wait…')
        UpgradePluginThread(self.window).start()


class UpgradePluginThread(threading.Thread, PluginInstaller):
    def __init__(self, window):
        self.window = window
        self.completion_type = 'upgraded'
        threading.Thread.__init__(self)
        PluginInstaller.__init__(self)

    def run(self):
        self.package_list = self.make_package_list(['install'])
        def show_quick_panel():
            self.window.show_quick_panel(self.package_list, self.on_done)
        sublime.set_timeout(show_quick_panel, 0)


class ExistingPluginsCommand():
    def __init__(self):
        self.manager = PluginManager()

    def make_package_list(self):
        packages = self.manager.list_packages()

        package_list = []
        for package in sorted(packages):
            package_entry = [package]
            metadata = self.manager.get_metadata(package)

            package_entry.append(metadata.get('description',
                'No description provided'))

            version = metadata.get('version')
            if version:
                version = 'v' + version
            else:
                version = 'unknown version'

            url = metadata.get('url')
            if url:
                url = re.sub('^https?://', '', url)
                url += '; '
            else:
                url = ''

            package_entry.append(version + '; ' + url + 'action: remove')
            package_list.append(package_entry)

        return package_list


class ListPluginsCommand(sublime_plugin.WindowCommand):
    def run(self):
        ListPluginsThread(self.window).start()


class ListPluginsThread(threading.Thread, ExistingPluginsCommand):
    def __init__(self, window):
        self.window = window
        threading.Thread.__init__(self)
        ExistingPluginsCommand.__init__(self)

    def run(self):
        self.package_list = self.make_package_list()

        def show_quick_panel():
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


class RemovePluginCommand(sublime_plugin.WindowCommand):
    def run(self):
        RemovePluginThread(self.window).start()


class RemovePluginThread(threading.Thread, ExistingPluginsCommand):
    def __init__(self, window):
        self.window = window
        threading.Thread.__init__(self)
        ExistingPluginsCommand.__init__(self)

    def run(self):
        self.package_list = self.make_package_list()

        def show_quick_panel():
            self.window.show_quick_panel(self.package_list, self.on_done)
        sublime.set_timeout(show_quick_panel, 0)

    def on_done(self, picked):
        if picked == -1:
            return
        package = self.package_list[picked][0]
        self.manager.remove_package(package)
        sublime.status_message('Plugin ' + package + ' successfully removed')


class AddRepositoryChannelCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.show_input_panel('Repository Channel URL', '',
            self.on_done, self.on_change, self.on_cancel)

    def on_done(self, input):
        settings = sublime.load_settings('Plugin Manager.sublime-settings')
        repository_channels = settings.get('repository_channels', [])
        if not repository_channels:
            repository_channels = []
        repository_channels.append(input)
        settings.set('repository_channels', repository_channels)
        sublime.save_settings('Plugin Manager.sublime-settings')

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass


class AddRepositoryCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.show_input_panel('Repository URL', '', self.on_done,
            self.on_change, self.on_cancel)

    def on_done(self, input):
        settings = sublime.load_settings('Plugin Manager.sublime-settings')
        repositories = settings.get('repositories', [])
        if not repositories:
            repositories = []
        repositories.append(input)
        settings.set('repositories', repositories)
        sublime.save_settings('Plugin Manager.sublime-settings')

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass


class AutomaticUpgrader(threading.Thread):
    def __init__(self):
        self.installer = PluginInstaller()
        self.auto_upgrade = PluginManager().settings.get('auto_upgrade')
        threading.Thread.__init__(self)

    def run(self):
        if self.auto_upgrade:
            packages = self.installer.make_package_list(['install', 'reinstall',
                'downgrade', 'overwrite unknown'])
            if not packages:
                return

            print 'Plugin Manager: Installing %s upgrades' % len(packages)
            for package in packages:
                self.installer.install_package(package[0])
                print 'Plugin Manager: Upgraded %s to %s' % (package[0],
                    re.sub(' .*$', '', package[1]))

AutomaticUpgrader().start()