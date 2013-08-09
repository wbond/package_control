import re

from .semver import SemVer
from .console_write import console_write


def semver_compat(v):
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
        v = '0.%s.%s+%s.%s.%s.%s' % date_match.groups()

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
    output = []
    for version in versions:
        if SemVer(semver_compat(version)).prerelease != None:
            continue
        output.append(version)
    return output


def version_filter(versions, allow_prerelease=False):
    output = []
    for version in versions:
        no_v_version = re.sub('^v', '', version)
        if not SemVer.valid(no_v_version):
            continue
        if not allow_prerelease and SemVer(no_v_version).prerelease != None:
            continue
        output.append(version)
    return output


def _version_sort_key(item):
    return SemVer(semver_compat(item))


def version_sort(sortable, **kwargs):
    try:
        return sorted(sortable, key=_version_sort_key, **kwargs)
    except (ValueError) as e:
        console_write(u"Error sorting versions - %s" % e, True)
        return []
