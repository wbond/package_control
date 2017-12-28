import re

from ..package_manager import PackageManager


class ExistingPackagesCommand(object):

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
        for package in packages:
            package_entry = [package]
            metadata = self.manager.get_metadata(package)

            description = metadata.get('description')
            if not description:
                description = 'No description provided'
            package_entry.append(description)

            version = metadata.get('version')
            if not version and self.manager.is_git_package(package):
                installed_version = 'git repository'
            elif not version and self.manager.is_hg_package(package):
                installed_version = 'hg repository'
            else:
                installed_version = 'v' + version if version else 'unknown version'

            url = metadata.get('url')
            if url:
                url = '; ' + re.sub('^https?://', '', url)
            else:
                url = ''

            package_entry.append(action + installed_version + url)
            package_list.append(package_entry)

        return package_list
