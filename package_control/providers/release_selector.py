import re
import sublime

from ..versions import version_exclude_prerelease


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

    platform_selectors = [
        sublime.platform() + '-' + sublime.arch(),
        sublime.platform(),
        '*'
    ]

    install_prereleases = settings.get('install_prereleases')
    allow_prereleases = install_prereleases is True
    if not allow_prereleases and isinstance(install_prereleases, list) and package in install_prereleases:
        allow_prereleases = True

    if not allow_prereleases:
        releases = version_exclude_prerelease(releases)

    output = []
    st_version = int(sublime.version())
    for release in releases:
        platforms = release.get('platforms', '*')
        if not isinstance(platforms, list):
            platforms = [platforms]
        for selector in platform_selectors:
            if selector in platforms:
                break
        else:
            continue
        # Default to '*' (for legacy reasons), see #604
        if not is_compatible_version(release.get('sublime_text', '*'), st_version):
            continue

        output.append(release)

    return output


def is_compatible_version(version_range, st_version):
    if version_range == '*':
        return True

    gt_match = re.match(r'>(\d{4})$', version_range)
    if gt_match:
        return st_version > int(gt_match.group(1))

    ge_match = re.match(r'>=(\d{4})$', version_range)
    if ge_match:
        return st_version >= int(ge_match.group(1))

    lt_match = re.match(r'<(\d{4})$', version_range)
    if lt_match:
        return st_version < int(lt_match.group(1))

    le_match = re.match(r'<=(\d{4})$', version_range)
    if le_match:
        return st_version <= int(le_match.group(1))

    range_match = re.match(r'(\d{4}) - (\d{4})$', version_range)
    if range_match:
        return st_version >= int(range_match.group(1)) and st_version <= int(range_match.group(2))

    return None
