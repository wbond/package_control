import datetime
import html
import os
import re

import sublime
import sublime_plugin

from .. import package_io
from ..package_manager import PackageManager
from ..show_error import show_message

USE_QUICK_PANEL_ITEM = hasattr(sublime, 'QuickPanelItem')


class ExistingPackagesCommand(sublime_plugin.ApplicationCommand):

    """
    Allows listing installed packages and their current version
    """

    def run(self):
        manager = PackageManager()

        action = self.action()
        if action:
            action += ' '

        default_packages = manager.list_default_packages()
        default_version = 'built-in v' + sublime.version()

        url_pattern = re.compile(r'^https?://')

        package_list = []
        for package in sorted(self.list_packages(manager), key=lambda s: s.lower()):
            if package in default_packages:
                description = 'Bundled Sublime Text Package'
                installed_version = default_version
                install_time = None
                upgrade_time = None
                url = ''

            else:
                metadata = manager.get_metadata(package)
                package_dir = package_io.get_package_dir(package)

                description = metadata.get('description')
                if not description:
                    description = 'No description provided'

                version = metadata.get('version')
                if not version and os.path.exists(os.path.join(package_dir, '.git')):
                    installed_version = 'git repository'
                elif not version and os.path.exists(os.path.join(package_dir, '.hg')):
                    installed_version = 'hg repository'
                else:
                    installed_version = 'v' + version if version else 'unknown version'

                install_time = metadata.get('install_time')
                upgrade_time = metadata.get('upgrade_time')

                url = metadata.get('url', '')

            if USE_QUICK_PANEL_ITEM:
                description = '<em>%s</em>' % html.escape(description)
                final_line = '<em>' + action + installed_version + '</em>'
                url = html.escape(url)
                url_display = url_pattern.sub('', url)
                if url_display:
                    final_line += '; <a href="%s">%s</a>' % (url, url_display)

                annotation = ''
                if upgrade_time:
                    annotation = datetime.datetime.fromtimestamp(upgrade_time).strftime('Updated at %c')
                elif install_time:
                    annotation = datetime.datetime.fromtimestamp(install_time).strftime('Installed at %c')

                package_entry = sublime.QuickPanelItem(package, [description, final_line], annotation)
            else:
                final_line = action + installed_version
                url_display = url_pattern.sub('', url)
                if url_display:
                    final_line += '; ' + url_display
                package_entry = [package, description, final_line]

            package_list.append(package_entry)

        if not package_list:
            show_message(self.no_packages_error())
            return

        def on_done(index):
            if index == -1:
                return

            if USE_QUICK_PANEL_ITEM:
                package_name = package_list[index].trigger
            else:
                package_name = package_list[index][0]

            self.on_done(manager, package_name)

        sublime.active_window().show_quick_panel(
            package_list,
            on_done,
            sublime.KEEP_OPEN_ON_FOCUS_LOST
        )

    def action(self):
        """
        Build a strng to describe the action taken on selected package.
        """

        return ""

    def list_packages(self, manager):
        """
        Build a list of packages to display.

        :param manager:
            The package manager instance to use.

        :returns:
            A list of package names to add to the quick panel
        """

        raise NotImplementedError()

    def no_packages_error(self):
        """
        Return the error message to display if no packages are availablw.
        """

        raise NotImplementedError()

    def on_done(self, manager, package_name):
        """
        Callback function to perform action on selected package.

        :param manager:
            The package manager instance to use.

        :param package_name:
            A package name to perform action for
        """

        raise NotImplementedError()
