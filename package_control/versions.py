import re

from .semver import SemVer
from .console_write import console_write


def semver_compat(v):
    """
    Converts a string version number into SemVer. If the version is based on
    a date, converts to 0.0.1+yyyy.mm.dd.hh.mm.ss.

    :param v:
        A string, dict with 'version' key, or a SemVer object

    :return:
        A string that is a valid semantic version number
    """

    if isinstance(v, SemVer):
        return str(v)

    # Allowing passing in a dict containing info about a package
    if isinstance(v, dict):
        if 'version' not in v:
            return '0'
        v = v['version']

    # Trim v off of the front
    v = re.sub('^v', '', v)

    # We prepend 0 to all date-based version numbers so that developers
    # may switch to explicit versioning from GitHub/BitBucket
    # versioning based on commit dates.
    #
    # When translating dates into semver, the way to get each date
    # segment into the version is to treat the year and month as
    # minor and patch, and then the rest as a numeric build version
    # with four different parts. The result looks like:
    # 0.2012.11+10.31.23.59
    date_match = re.match('(\d{4})\.(\d{2})\.(\d{2})\.(\d{2})\.(\d{2})\.(\d{2})$', v)
    if date_match:
        v = '0.0.1+%s.%s.%s.%s.%s.%s' % date_match.groups()

    # This handles version that were valid pre-semver with 4+ dotted
    # groups, such as 1.6.9.0
    four_plus_match = re.match('(\d+\.\d+\.\d+)[T\.](\d+(\.\d+)*)$', v)
    if four_plus_match:
        v = '%s+%s' % (four_plus_match.group(1), four_plus_match.group(2))

    # Semver must have major, minor, patch
    elif re.match('^\d+$', v):
        v += '.0.0'
    elif re.match('^\d+\.\d+$', v):
        v += '.0'
    return v


def version_comparable(string):
    return SemVer(semver_compat(string))


def version_exclude_prerelease(versions):
    """
    Remove prerelease versions for a list of SemVer versions

    :param versions:
        The list of versions to filter

    :return:
        The list of versions with pre-releases removed
    """

    output = []
    for version in versions:
        if SemVer(semver_compat(version)).prerelease != None:
            continue
        output.append(version)
    return output


def version_process(versions, filter_prefix):
    """
    Filter a list of versions to ones that are valid SemVers, if a prefix
    is provided, only match versions starting with the prefix and split

    :param versions:
        The list of versions to filter

    :param filter_prefix:
        Remove this prefix from the version before checking if it is a valid
        SemVer. If this prefix is not present, skip the version.

    :return:
        A list of dicts, each of which has the keys "version" and "prefix"
    """

    output = []
    for version in versions:
        prefix = ''

        if filter_prefix:
            if version[0:len(filter_prefix)] != filter_prefix:
                continue
            check_version = version[len(filter_prefix):]
            prefix = filter_prefix

        else:
            check_version = re.sub('^v', '', version)
            if check_version != version:
                prefix = 'v'

        if not SemVer.valid(check_version):
            continue

        output.append({'version': check_version, 'prefix': prefix})
    return output


def version_sort(sortable, *fields, **kwargs):
    """
    Sorts a list that is a list of versions, or dicts with a 'version' key.
    Can also secondly sort by another field.

    :param sortable:
        The list to sort

    :param *fields:
        If sortable is a list of dicts, perform secondary sort via these fields,
        in order

    :param **kwargs:
        Keyword args to pass on to sorted()

    :return:
        A copy of sortable that is sorted according to SemVer rules
    """

    def _version_sort_key(item):
        result = SemVer(semver_compat(item))
        if fields:
            values = [result]
            for field in fields:
                values.append(item[field])
            result = tuple(values)
        return result

    try:
        return sorted(sortable, key=_version_sort_key, **kwargs)
    except (ValueError) as e:
        console_write(u"Error sorting versions - %s" % e, True)
        return []
