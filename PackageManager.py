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
		package_dirs = [path for path in package_paths if os.path.isdir(os.path.join(sublime.packages_path(), path))]
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
				output[package['name']] = {
					'name': package['name'],
					'description': package['description'],
					'package_filename': package['package_filename'],
					'downloads': downloads,
					'repo': repo,
					'installed': package['name'] in installed_packages
					}
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
			sublime.error_message('The folder for the package name specified,' +
				' %s, does not exist in %s' % (package_name,
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
		packages = self.list_packages()

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
		return True


class PackageManagerPanel():
	def write(self, string):
		if not hasattr(self, 'panel'):
			self.window = sublime.active_window()
			self.panel  = self.window.get_output_panel('PackageManager')
			self.panel.settings().set("word_wrap", True)
			self.panel.set_read_only(True)

		self.window.run_command('show_panel', {'panel':
			'output.PackageManager'})
		self.panel.set_read_only(False)
		edit = self.panel.begin_edit()

		while self.panel.size() == 0 and string[0] == '\n':
			string = string[1:]

		regions = self.panel.get_regions('PackageManager')
		region = sublime.Region(self.panel.size(), self.panel.size() +
			len(string))
		regions.append(region)
		self.panel.add_regions('PackageManager', regions, 'string',
			sublime.PERSISTENT)
		self.panel.insert(edit, self.panel.size(), string)
		self.panel.show(self.panel.size())
		self.panel.end_edit(edit)
		self.panel.set_read_only(True)


class ListPackagesCommand(sublime_plugin.WindowCommand, PackageManagerPanel):
	def run(self):
		manager = PackageManager()
		packages = manager.list_available_packages()

		self.write("\n\nAvailable packages:")
		for package in sorted(packages.iterkeys()):
			info = packages[package]
			installed = ('Installed' if info['installed'] else 'Not installed')
			download = info['downloads'][0]
			self.write("\n  " + package)
			self.write("\n    v" + download['version'] + ', ' +
				download['date'])
			self.write("\n    " + installed + ', ' + info['repo'])


class CreatePackageCommand(sublime_plugin.WindowCommand, PackageManagerPanel):
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


class InstallPackageCommand(sublime_plugin.WindowCommand, PackageManagerPanel):
	def run(self):
		view = self.window.show_input_panel('Package To Install', '',
			self.on_done, self.on_change, self.on_cancel)

	def on_done(self, package_name):
		manager = PackageManager()
		manager.install_package(package_name)

	def on_change(self, text):
		pass

	def on_cancel(self):
		pass