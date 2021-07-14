import re
import threading
import time

import sublime

from .thread_progress import ThreadProgress
from .package_manager import PackageManager
from .package_disabler import PackageDisabler
from .versions import version_comparable

USE_QUICK_PANEL_ITEM = hasattr(sublime, 'QuickPanelItem')


class PackageInstaller(PackageDisabler):

    """
    Provides helper functionality related to installing packages
    """

    def __init__(self):
        self.manager = PackageManager()
        # Track what the color scheme was before upgrade so we can restore it
        self.old_color_scheme_package = None
        self.old_color_scheme = None
        # Track what the theme was before upgrade so we can restore it
        self.old_theme_package = None
        self.old_theme = None

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
            settings = self.manager.settings

            if override_action:
                action = override_action
                extra = ''

            else:
                if self.manager.is_vcs_package(package):
                    to_ignore = settings.get('ignore_vcs_packages')
                    if to_ignore is True:
                        continue
                    if isinstance(to_ignore, list) and package in to_ignore:
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
                        installed_version = version_comparable(installed_version)
                        new_version_cmp = version_comparable(release['version'])
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

            homepage = info['homepage']
            homepage_display = re.sub('^https?://', '', homepage)

            if USE_QUICK_PANEL_ITEM:
                description = '<em>%s</em>' % sublime.html_format_command(description)
                final_line = '<em>' + action + extra + '</em>'
                if homepage_display:
                    if action or extra:
                        final_line += ' '
                    final_line += '<a href="%s">%s</a>' % (
                        sublime.html_format_command(homepage),
                        sublime.html_format_command(homepage_display),
                    )
                package_entry = sublime.QuickPanelItem(package, [description, final_line])
            else:
                package_entry = [package]
                package_entry.append(description)
                final_line = action + extra
                if final_line and homepage_display:
                    final_line += ' '
                final_line += homepage_display
                package_entry.append(final_line)

            package_list.append(package_entry)
        return package_list

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
        if USE_QUICK_PANEL_ITEM:
            name = self.package_list[picked].trigger
        else:
            name = self.package_list[picked][0]

        if name in self.disable_packages(name, 'install'):
            def on_complete():
                self.reenable_package(name, 'install')
        else:
            on_complete = None

        thread = PackageInstallerThread(self.manager, name, on_complete)
        thread.start()
        ThreadProgress(
            thread,
            'Installing package %s' % name,
            'Package %s successfully %s' % (name, self.completion_type)
        )


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
