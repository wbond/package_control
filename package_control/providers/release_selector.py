import re
import sublime

from ..versions import version_sort, version_exclude_prerelease


class ReleaseSelector():
    """
    A base class for finding the best version of a package for the current machine
    """

    def select_release(self, package_info):
        """
        Returns a modified package info dict for package from package schema version 2.0

        :param package_info:
            A package info dict with a "releases" key

        :return:
            The package info dict with the "releases" key deleted, and a
            "download" key added that contains a dict with "version", "url" and
            "date" keys.
            None if no compatible relases are available.
        """

        releases = version_sort(package_info['releases'])
        if not self.settings.get('install_prereleases'):
            releases = version_exclude_prerelease(releases)

        for release in releases:
            platforms = release.get('platforms', '*')
            if not isinstance(platforms, list):
                platforms = [platforms]

            best_platform = self.get_best_platform(platforms)
            if not best_platform:
                continue

            if not self.is_compatible_version(release.get('sublime_text', '<3000')):
                continue

            package_info['download'] = release
            package_info['last_modified'] = release.get('date')
            del package_info['releases']

            return package_info

        return None

    def select_platform(self, package_info):
        """
        Returns a modified package info dict for package from package schema version <= 1.2

        :param package_info:
            A package info dict with a "platforms" key

        :return:
            The package info dict with the "platforms" key deleted, and a
            "download" key added that contains a dict with "version" and "url"
            keys.
            None if no compatible platforms.
        """
        platforms = list(package_info['platforms'].keys())
        best_platform = self.get_best_platform(platforms)
        if not best_platform:
            return None

        package_info['download'] = package_info['platforms'][best_platform][0]
        package_info['download']['date'] = package_info.get('last_modified')
        del package_info['platforms']

        return package_info

    def get_best_platform(self, platforms):
        """
        Returns the most specific platform that matches the current machine

        :param platforms:
            An array of platform names for a package. E.g. ['*', 'windows', 'linux-x64']

        :return: A string reprenting the most specific matching platform
        """

        ids = [sublime.platform() + '-' + sublime.arch(), sublime.platform(),
            '*']

        for id in ids:
            if id in platforms:
                return id

        return None

    def is_compatible_version(self, version_range):
        min_version = float("-inf")
        max_version = float("inf")

        if version_range == '*':
            return True

        gt_match = re.match('>(\d+)$', version_range)
        ge_match = re.match('>=(\d+)$', version_range)
        lt_match = re.match('<(\d+)$', version_range)
        le_match = re.match('<=(\d+)$', version_range)
        range_match = re.match('(\d+) - (\d+)$', version_range)

        if gt_match:
            min_version = int(gt_match.group(1)) + 1
        elif ge_match:
            min_version = int(ge_match.group(1))
        elif lt_match:
            max_version = int(lt_match.group(1)) - 1
        elif le_match:
            max_version = int(le_match.group(1))
        elif range_match:
            min_version = int(range_match.group(1))
            max_version = int(range_match.group(2))
        else:
            return None

        if min_version > int(sublime.version()):
            return False
        if max_version < int(sublime.version()):
            return False

        return True
