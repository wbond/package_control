import re
import sublime

from ..versions import version_sort, version_exclude_prerelease



def filter_releases(package, settings, releases):
    """
    Returns all releases in the list of releases that are compatible with
    the current platform and version of Sublime Text

    :param package:
        The name of the package

    :param settings:
        A dict optionally containing the `install_prereleases` key

    :param releases:
        A list of release dicts

    :return:
        A list of release dicts
    """

    platform_selectors = [sublime.platform() + '-' + sublime.arch(),
        sublime.platform(), '*']

    install_prereleases = settings.get('install_prereleases')
    allow_prereleases = install_prereleases is True
    if not allow_prereleases and isinstance(install_prereleases, list) and package in install_prereleases:
        allow_prereleases = True

    if not allow_prereleases:
        releases = version_exclude_prerelease(releases)

    output = []
    for release in releases:
        platforms = release.get('platforms', '*')
        if not isinstance(platforms, list):
            platforms = [platforms]

        matched = False
        for selector in platform_selectors:
            if selector in platforms:
                matched = True
                break
        if not matched:
            continue

        # Default to '*' (for legacy reasons), see #604
        if not is_compatible_version(release.get('sublime_text', '*')):
            continue

        output.append(release)

    return output


def is_compatible_version(version_range):
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
