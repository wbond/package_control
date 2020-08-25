import os
import re

import sublime

from ..package_manager import PackageManager

USE_QUICK_PANEL_ITEM = int(sublime.version()) > 4080

class ExistingPackagesCommand():

    """
    Allows listing installed packages and their current version
    """

    def __init__(self):
        self.manager = PackageManager()

    def make_package_list(self, action=''):
        """
        Returns a list of installed packages suitable for displaying in the
        quick panel.

        :param action:
            An action to display at the beginning of the third element of the
            list returned for each package

        :return:
            A list of lists, each containing three strings:
              0 - package name
              1 - package description
              2 - [action] installed version; package url
        """

        packages = self.manager.list_packages()

        if action:
            action += ' '

        package_list = []
        for package in sorted(packages, key=lambda s: s.lower()):
            metadata = self.manager.get_metadata(package)
            package_dir = os.path.join(sublime.packages_path(), package)

            description = metadata.get('description')
            if not description:
                description = 'No description provided'
                if USE_QUICK_PANEL_ITEM:
                    description = '<em>%s</em>' % description

            version = metadata.get('version')
            if not version and os.path.exists(os.path.join(package_dir, '.git')):
                installed_version = 'git repository'
            elif not version and os.path.exists(os.path.join(package_dir, '.hg')):
                installed_version = 'hg repository'
            else:
                installed_version = 'v' + version if version else 'unknown version'

            homepage = metadata.get('url', '')
            homepage_display= re.sub('^https?://', '', homepage)

            if USE_QUICK_PANEL_ITEM:
                final_line = '<em>' + action + installed_version + ';</em>'
                if final_line and homepage:
                    final_line += ' '
                final_line += '<a href="%s">%s</a>' % (homepage, homepage_display)
                package_entry = sublime.QuickPanelItem(package, [description, final_line])
            else:
                package_entry = [package]
                package_entry.append(description)
                final_line = action + installed_version + ';'
                if final_line and homepage_display:
                    final_line += ' '
                final_line += homepage_display
                package_entry.append(final_line)
            package_list.append(package_entry)

        return package_list
