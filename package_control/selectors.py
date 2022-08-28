import re
import sublime

PLATFORM_SELECTORS = (
    sublime.platform() + '-' + sublime.arch(),
    sublime.platform(),
    '*'
)

ST_VERSION = int(sublime.version())


def get_compatible_platform(platforms, platform_selectors=PLATFORM_SELECTORS):
    """
    Gets the platform, which is compatible with OS.

    :param platforms:
        A list of platforms to choose from

    :param platform_selectors:
        A list of platform selectors to match against
        Defaults to ``PLATFORM_SELECTORS``

    :returns:
        The compatible platform from ``platforms`` or
        False, if none was found in ``platforms``
    """

    if not isinstance(platforms, list):
        platforms = [platforms]

    for selector in platform_selectors:
        if selector in platforms:
            return selector

    return False


def is_compatible_platform(platforms, platform_selectors=PLATFORM_SELECTORS):
    """
    Checks if platforms are compatible with OS.

    :param platforms:
        A list of platforms to choose from

    :param platform_selectors:
        A list of platform selectors to match against
        Defaults to ``PLATFORM_SELECTORS``

    :returns:
        True, if a compatible platform was found in ``platforms``
        False, if none was found
    """

    return bool(get_compatible_platform(platforms, platform_selectors))


def is_compatible_version(version_range, st_version=ST_VERSION):
    """
    Determines if current ST version is covered by given version range.

    :param version_range:
        The version range expression to match ST version against.

        Examples: ">4000", ">=4000", "<4000", "<=4000", "4000 - 4100"

    :param st_version:
        The ST version to evaluate. Defaults to ``ST_VERSION``

    :returns:
        True if compatible version, False otherwise.
    """

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
