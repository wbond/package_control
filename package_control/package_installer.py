import html
import re
import threading
import time

import sublime

from .package_manager import PackageManager
from .package_disabler import PackageDisabler
from .versions import PackageVersion

USE_QUICK_PANEL_ITEM = hasattr(sublime, 'QuickPanelItem')


class PackageInstaller(PackageDisabler):

    """
    Provides helper functionality related to installing packages
    """

    def __init__(self):
        self.manager = PackageManager()

    def make_package_list(self, ignore_actions=[], override_action=None, ignore_packages=[]):
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

        url_pattern = re.compile(r'^https?://')

        ignore_vcs_packages = 'pull' in ignore_actions
        if not ignore_vcs_packages:
            ignore_vcs_packages = self.manager.settings.get('ignore_vcs_packages')

        package_list = []
        for package in sorted(iter(packages.keys()), key=lambda s: s.lower()):
            if ignore_packages and package in ignore_packages:
                continue
            info = packages[package]
            release = info['releases'][0]

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
            new_version = 'v' + release['version']

            vcs = None

            if override_action:
                action = override_action
                extra = ''

            else:
                if self.manager.is_vcs_package(package):
                    if ignore_vcs_packages is True:
                        continue
                    if isinstance(ignore_vcs_packages, list) and package in ignore_vcs_packages:
                        continue
                    upgrader = self.manager.instantiate_upgrader(package)
                    vcs = upgrader.cli_name
                    incoming = upgrader.incoming()

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
                        extra = ' %s with %s' % (installed_version_name, new_version)
                    else:
                        installed_version = PackageVersion(installed_version)
                        new_version_cmp = PackageVersion(release['version'])
                        if new_version_cmp > installed_version:
                            action = 'upgrade'
                            extra = ' to %s from %s' % (new_version, installed_version_name)
                        elif new_version_cmp < installed_version:
                            action = 'downgrade'
                            extra = ' to %s from %s' % (new_version, installed_version_name)
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

            if USE_QUICK_PANEL_ITEM:
                description = '<em>%s</em>' % html.escape(description)
                final_line = '<em>' + action + extra + '</em>'
                homepage = html.escape(info['homepage'])
                homepage_display = url_pattern.sub('', homepage)
                if homepage_display:
                    if action or extra:
                        final_line += ' '
                    final_line += '<a href="%s">%s</a>' % (homepage, homepage_display)
                package_entry = sublime.QuickPanelItem(package, [description, final_line])
            else:
                package_entry = [package]
                package_entry.append(description)
                final_line = action + extra
                homepage_display = url_pattern.sub('', info['homepage'])
                if final_line and homepage_display:
                    final_line += ' '
                final_line += homepage_display
                package_entry.append(final_line)

            package_list.append(package_entry)
        return package_list


class PackageInstallerThread(threading.Thread):

    """
    A thread to run package install/upgrade operations in so that the main
    Sublime Text thread does not get blocked and freeze the UI
    """

    def __init__(self, manager, package, on_complete, pause=False):
        """
        :param manager:
            An instance of :class:`PackageManager`

        :param package:
            The string package name to install/upgrade

        :param on_complete:
            A callback to run after installing/upgrading the package

        :param pause:
            If we should pause before upgrading to allow a package to be
            fully disabled.
        """

        self.package = package
        self.manager = manager
        self.on_complete = on_complete
        self.pause = pause
        threading.Thread.__init__(self)

    def run(self):
        if self.pause:
            time.sleep(0.7)
        try:
            self.result = self.manager.install_package(self.package)
        except (Exception):
            self.result = False
            raise
        finally:
            # Do not reenable if deferred until next restart
            if self.on_complete and self.result is not None:
                sublime.set_timeout(self.on_complete, 700)
