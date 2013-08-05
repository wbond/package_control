import os
import re
import threading

import sublime

from .preferences_filename import preferences_filename
from .thread_progress import ThreadProgress
from .package_manager import PackageManager
from .upgraders.git_upgrader import GitUpgrader
from .upgraders.hg_upgrader import HgUpgrader
from .versions import version_comparable


class PackageInstaller():
    """
    Provides helper functionality related to installing packages
    """

    def __init__(self):
        self.manager = PackageManager()

    def make_package_list(self, ignore_actions=[], override_action=None,
            ignore_packages=[]):
        """
        Creates a list of packages and what operation would be performed for
        each. Allows filtering by the applicable action or package name.
        Returns the information in a format suitable for displaying in the
        quick panel.

        :param ignore_actions:
            A list of actions to ignore packages by. Valid actions include:
            `install`, `upgrade`, `downgrade`, `reinstall`, `overwrite`,
            `pull` and `none`. `pull` andd `none` are for Git and Hg
            repositories. `pull` is present when incoming changes are detected,
            where as `none` is selected if no commits are available. `overwrite`
            is for packages that do not include version information via the
            `package-metadata.json` file.

        :param override_action:
            A string action name to override the displayed action for all listed
            packages.

        :param ignore_packages:
            A list of packages names that should not be returned in the list

        :return:
            A list of lists, each containing three strings:
              0 - package name
              1 - package description
              2 - action; [extra info;] package url
        """

        packages = self.manager.list_available_packages()
        installed_packages = self.manager.list_packages()

        package_list = []
        for package in sorted(iter(packages.keys()), key=lambda s: s.lower()):
            if ignore_packages and package in ignore_packages:
                continue
            package_entry = [package]
            info = packages[package]
            download = info['download']

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

            vcs = None
            package_dir = self.manager.get_package_dir(package)
            settings = self.manager.settings

            if override_action:
                action = override_action
                extra = ''

            else:
                if os.path.exists(os.path.join(package_dir, '.git')):
                    if settings.get('ignore_vcs_packages'):
                        continue
                    vcs = 'git'
                    incoming = GitUpgrader(settings.get('git_binary'),
                        settings.get('git_update_command'), package_dir,
                        settings.get('cache_length'), settings.get('debug')
                        ).incoming()
                elif os.path.exists(os.path.join(package_dir, '.hg')):
                    if settings.get('ignore_vcs_packages'):
                        continue
                    vcs = 'hg'
                    incoming = HgUpgrader(settings.get('hg_binary'),
                        settings.get('hg_update_command'), package_dir,
                        settings.get('cache_length'), settings.get('debug')
                        ).incoming()

                if installed:
                    if vcs:
                        if incoming:
                            action = 'pull'
                            extra = ' with ' + vcs
                        else:
                            action = 'none'
                            extra = ''
                    elif not installed_version:
                        action = 'overwrite'
                        extra = ' %s with %s' % (installed_version_name,
                            new_version)
                    else:
                        installed_version = version_comparable(installed_version)
                        download_version = version_comparable(download['version'])
                        if download_version > installed_version:
                            action = 'upgrade'
                            extra = ' to %s from %s' % (new_version,
                                installed_version_name)
                        elif download_version < installed_version:
                            action = 'downgrade'
                            extra = ' to %s from %s' % (new_version,
                                installed_version_name)
                        else:
                            action = 'reinstall'
                            extra = ' %s' % new_version
                else:
                    action = 'install'
                    extra = ' %s' % new_version
                extra += ';'

                if action in ignore_actions:
                    continue

            description = info.get('description')
            if not description:
                description = 'No description provided'
            package_entry.append(description)
            package_entry.append(action + extra + ' ' +
                re.sub('^https?://', '', info['homepage']))
            package_list.append(package_entry)
        return package_list

    def disable_packages(self, packages):
        """
        Disables one or more packages before installing or upgrading to prevent
        errors where Sublime Text tries to read files that no longer exist, or
        read a half-written file.

        :param packages: The string package name, or an array of strings
        """

        if not isinstance(packages, list):
            packages = [packages]

        # Don't disable Package Control so it does not get stuck disabled
        if 'Package Control' in packages:
            packages.remove('Package Control')

        disabled = []

        settings = sublime.load_settings(preferences_filename())
        ignored = settings.get('ignored_packages')
        if not ignored:
            ignored = []
        for package in packages:
            if not package in ignored:
                ignored.append(package)
                disabled.append(package)
        settings.set('ignored_packages', ignored)
        sublime.save_settings(preferences_filename())
        return disabled

    def reenable_package(self, package):
        """
        Re-enables a package after it has been installed or upgraded

        :param package: The string package name
        """

        settings = sublime.load_settings(preferences_filename())
        ignored = settings.get('ignored_packages')
        if not ignored:
            return
        if package in ignored:
            settings.set('ignored_packages',
                list(set(ignored) - set([package])))
            sublime.save_settings(preferences_filename())

    def on_done(self, picked):
        """
        Quick panel user selection handler - disables a package, installs or
        upgrades it, then re-enables the package

        :param picked:
            An integer of the 0-based package name index from the presented
            list. -1 means the user cancelled.
        """

        if picked == -1:
            return
        name = self.package_list[picked][0]

        if name in self.disable_packages(name):
            on_complete = lambda: self.reenable_package(name)
        else:
            on_complete = None

        thread = PackageInstallerThread(self.manager, name, on_complete)
        thread.start()
        ThreadProgress(thread, 'Installing package %s' % name,
            'Package %s successfully %s' % (name, self.completion_type))


class PackageInstallerThread(threading.Thread):
    """
    A thread to run package install/upgrade operations in so that the main
    Sublime Text thread does not get blocked and freeze the UI
    """

    def __init__(self, manager, package, on_complete):
        """
        :param manager:
            An instance of :class:`PackageManager`

        :param package:
            The string package name to install/upgrade

        :param on_complete:
            A callback to run after installing/upgrading the package
        """

        self.package = package
        self.manager = manager
        self.on_complete = on_complete
        threading.Thread.__init__(self)

    def run(self):
        try:
            self.result = self.manager.install_package(self.package)
        finally:
            if self.on_complete:
                sublime.set_timeout(self.on_complete, 1)
