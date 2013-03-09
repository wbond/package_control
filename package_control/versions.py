import re

try:
    # Python 3
    from ..lib.all.semver import SemVer
except (ValueError):
    # Python 2
    from semver import SemVer

from .console_write import console_write


def semver_compat(v):
    # Allowing passing in a dict containing info about a package
    if isinstance(v, dict):
        if not hasattr(v, 'version'):
            return 0
        v = v['version']

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
    four_plus_match = re.match('(\d+\.\d+\.\d+)\.(\d+(\.\d+)*)$', v)
    if four_plus_match:
        v = '%s+%s' % (four_plus_match.group(1), four_plus_match.group(2))

    # Semver must have major, minor, patch
    elif re.match('^\d+$', v):
        v += '.0.0'
    elif re.match('^\d+\.\d+$', v):
        v += '.0'
    return v


def semver_cmp(version1, version2):
    """
    Compares to version strings to see which is greater

    Date-based version numbers (used by GitHub and BitBucket providers)
    are automatically pre-pended with a 0 so they are always less than
    version 1.0.

    :param version1:
        A string version number, or dict containing a "version" key

    :param version2:
        A string version number, or dict containing a "version" key

    :return:
        -1  if version1 is less than version2
         0  if they are equal
         1  if version1 is greater than version2
    """

    try:
        return semver.compare(semver_compat(version1), semver_compat(version2))
    except (ValueError) as e:
        console_write(u"Error comparing versions - %s" % e, True)
        return 0


def semver_filter(versions):
    output = []
    for version in versions:
        try:
            semver.parse(semver_compat(version))
            output.append(version)
        except (ValueError):
            pass
    return output


def _cmp_to_key(mycmp):
    'Convert a cmp= function into a key= function'
    class K(object):
        def __init__(self, obj, *args):
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0
        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0
        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0
        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0
        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0
        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
    return K


def semver_sort(sortable, **kwargs):
    sortable_compat = [SemVer(semver_compat(version)) for version in sortable]
    return sorted(sortable_compat, **kwargs)
