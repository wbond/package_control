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


class PackageManager():
    # Dirs and files to ignore when creating a package
    dirs_to_ignore = ['.hg', '.git', '.svn', '_darcs']
    files_to_ignore = ['.hgignore', '.gitignore', '.bzrignore', '*.pyc',
        '*.sublime-project', '*.tmTheme.cache']

    def compare_versions(self, version1, version2):
        def normalize(v):
            return [int(x) for x in re.sub(r'(\.0+)*$','', v).split(".")]
        return cmp(normalize(version1), normalize(version2))

    def list_repos(self):
        settings = sublime.load_settings('PackageManager.sublime-settings')
        return settings.get('repos')

    def list_available_packages(self):
        repos = self.list_repos()
        installed_packages = self.list_packages()
        packages = {}
        for repo in repos[::-1]:
            repo_info = json.load(urllib2.urlopen(repo))
            packages.update(self.extract_package_info(repo, repo_info,
                installed_packages))
        return packages

    def list_packages(self):
        package_paths = os.listdir(sublime.packages_path())
        package_dirs = [path for path in package_paths if
            os.path.isdir(os.path.join(sublime.packages_path(), path))]
        packages = list(set(package_dirs) - set(self.list_default_packages()))
        packages.sort()
        return packages

    def list_default_packages(self):
        files = os.listdir(sublime.packages_path() + '/../Pristine Packages/')
        files = list(set(files) - set(os.listdir(
            sublime.installed_packages_path())))
        packages = [file.replace('.sublime-package', '') for file in files]
        packages.sort()
        return packages

    def extract_package_info(self, repo, repo_info, installed_packages):
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
                    'description': package['description'],
                    'package_filename': package['package_filename'],
                    'downloads': downloads,
                    'repo': repo,
                    'installed': package['name'] in installed_packages
                }
                if info['installed']:
                    metadata_filename = os.path.join(sublime.packages_path(),
                        package['name'], 'package-metadata.json')
                    if os.path.exists(metadata_filename):
                        with open(metadata_filename) as f:
                            metadata = json.load(f)
                        info['installed_version'] = metadata['version']
                        info['installed_repo'] = metadata['repo']
                output[package['name']] = info
                break
        return output

    def md5sum(self, file):
        with open("filename", 'rb') as file:
            sum = hashlib.md5()
            while True:
                content = file.read(524288)
                if not content:
                    break
                sum.update(content)
        return sum.hexdigest()

    def create_package(self, package_name):
        package_dir = os.path.join(sublime.packages_path(), package_name) + '/'

        if not os.path.exists(package_dir):
            sublime.error_message('The folder for the package name ' +
                'specified, %s, does not exist in %s' % (package_name,
                sublime.packages_path()))
            return False

        package_filename = os.path.join(sublime.installed_packages_path(),
            package_name + '.sublime-package')

        if not os.path.exists(sublime.installed_packages_path()):
            os.mkdir(sublime.installed_packages_path())

        if os.path.exists(package_filename):
            os.remove(package_filename)

        package_file = zipfile.ZipFile(package_filename, "w")

        package_dir_regex = re.compile('^' + re.escape(package_dir))
        for root, dirs, files in os.walk(package_dir):
            [dirs.remove(dir) for dir in dirs if dir in self.dirs_to_ignore]
            paths = dirs
            paths.extend(files)
            for path in paths:
                if any(fnmatch(path, pattern) for pattern in
                        self.files_to_ignore):
                    continue
                full_path = os.path.join(root, path)
                relative_path = re.sub(package_dir_regex, '', full_path)
                package_file.write(full_path,
                    relative_path , zipfile.ZIP_DEFLATED)

        package_file.close()
        return True

    def install_package(self, package_name):
        installed_packages = self.list_packages()
        packages = self.list_available_packages()

        if package_name not in packages.keys():
            sublime.active_window().run_command('list_packages')
            sublime.error_message('The package specified,' +
                ' %s, is not available. The list of available packages is' +
                ' printed below.' % (package_name,))
            return False

        download = packages[package_name]['downloads'][0]
        url = download['url']
        package_filename = packages[package_name]['package_filename']
        package_path = os.path.join(sublime.installed_packages_path(),
            package_filename)

        try:
            package_file_http = urllib2.urlopen(url)

            package_file = open(package_path, "w")
            package_file.write(package_file_http.read())
            package_file.close()

        #handle errors
        except (HTTPError) as (e):
            sublime.error_message("HTTP Error " + e.code + ' downloading ' +
                url)
            return False
        except (URLError) as (e):
            sublime.error_message("URL Error " + e.reason + ' downloading ' +
                url)
            return False

        package_dir = os.path.join(sublime.packages_path(),
            package_filename.replace('.sublime-package', ''))
        if not os.path.exists(package_dir):
            os.mkdir(package_dir)

        package_zip = zipfile.ZipFile(package_path, 'r')
        for path in package_zip.namelist():
            if path[0] == '/' or path.find('..') != -1:
                sublime.error_message('The package specified,' +
                    ' %s, contains files outside of the package dir and' +
                    ' cannot be safely installed.' % (package_name,))
                return False

        os.chdir(package_dir)
        package_zip.extractall()
        package_metadata_file = os.path.join(package_dir,
            'package-metadata.json')
        with open(package_metadata_file, 'w') as f:
            metadata = {
                "version": packages[package_name]['downloads'][0]['version'],
                "repo": packages[package_name]['repo']
            }
            json.dump(metadata, f)
        return True


class CreatePackageCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.manager = PackageManager()
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


class PackageInstaller():
    def make_package_list(self, ignore_actions=[]):
        self.manager = PackageManager()
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
            package_entry.append('v' + download['version'] + ' (' +
                action + ') ' + re.sub('^https?://', '', info['repo']))
            package_list.append(package_entry)
        return package_list

    def on_done(self, picked):
        if picked == -1:
            return
        package_name = self.package_list[picked][0]
        self.install_package(package_name)

    def install_package(self, name):
        self.manager.install_package(name)


class InstallPackageCommand(sublime_plugin.WindowCommand, PackageInstaller):
    def run(self):
        self.package_list = self.make_package_list()
        self.window.show_quick_panel(self.package_list, self.on_done)


class UpgradePackageCommand(sublime_plugin.WindowCommand, PackageInstaller):
    def run(self):
        self.package_list = self.make_package_list(['install', 'reinstall',
            'downgrade'])
        self.window.show_quick_panel(self.package_list, self.on_done)


def automatic_upgrader():
    settings = sublime.load_settings('PackageManager.sublime-settings')
    if settings.get('auto_upgrade'):
        installer = PackageInstaller()
        packages = installer.make_package_list(['install', 'reinstall',
            'downgrade', 'overwrite unknown'])
        if not packages:
            return

        print 'PackageManager: Installing %s upgrades' % len(packages)
        for package in packages:
            installer.install_package(package[0])
            print 'PackageManager: Upgraded %s to %s' % (package[0],
                re.sub(' .*$', '', package[1]))

automatic_upgrader()