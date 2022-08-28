import re

from .deps.semver import SemVer
from .console_write import console_write


class PackageVersion(SemVer):

    _date_pattern = re.compile(r'^(\d{4})\.(\d{2})\.(\d{2})\.(\d{2})\.(\d{2})\.(\d{2})$')
    _pre_semver_pattern = re.compile(r'^(\d+)(?:\.(\d+)(?:\.(\d+)(?:[T\.](\d+(\.\d+)*))?)?)?$')

    @classmethod
    def _parse(cls, ver):
        """
        Converts a string version number into SemVer. If the version is based on
        a date, converts to 0.0.1+yyyy.mm.dd.hh.mm.ss.

        :param ver:
            A string, dict with 'version' key, or a SemVer object

        :raises:
            TypeError, if ver is not one of: str, dict with version, SemVer
            ValueError, if ver is no valid version string

        :return:
            A list of 5 items representing a valid semantic version number
        """

        # Allowing passing in a dict containing info about a package
        if isinstance(ver, dict):
            if 'version' not in ver:
                raise TypeError("%s is not a package or library release" % ver)
            ver = ver['version']

        if isinstance(ver, SemVer):
            return ver

        if not isinstance(ver, str):
            raise TypeError("%r is not a string" % ver)

        # Trim v off of the front
        if ver.startswith('v'):
            ver = ver[1:]

        # Match semver compatible strings
        match = cls._match_regex.match(ver)
        if match:
            g = list(match.groups())
            for i in range(3):
                g[i] = int(g[i])

            return g

        # We prepend 0 to all date-based version numbers so that developers
        # may switch to explicit versioning from GitHub/GitLab/BitBucket
        # versioning based on commit dates.
        #
        # The resulting semver is alwass 0.0.1 with timestamp being used
        # as build number, so any explicitly choosen version (via tags) will
        # be greater, once a package moves from branch to tag based releases.
        #
        # The result looks like:
        # 0.0.1+2020.07.15.10.50.38
        match = cls._date_pattern.match(ver)
        if match:
            return [0, 0, 1, None, '.'.join(match.groups())]

        # This handles versions that were valid pre-semver with 1 to 4+ dotted
        # groups, such as 1, 1.6, or 1.6.9.0
        match = cls._pre_semver_pattern.match(ver)
        if match:
            return [
                int(match.group(1) or 0),
                int(match.group(2) or 0),
                int(match.group(3) or 0),
                None,
                match.group(4)
            ]

        raise ValueError("'%s' is not a valid SemVer string" % ver)


def version_match_prefix(version, filter_prefix):
    """
    Create a SemVer for a given version, if it matches filter_prefix.

    :param version:
        The version string to match

    :param filter_prefix:
        The prefix to match versions against

    :returns:
        SemVer, if version is valid and matches given filter_prefix
        None, if version is invalid or doesn't match filter_prefix
    """

    try:
        if filter_prefix:
            if version.startswith(filter_prefix):
                return PackageVersion(version[len(filter_prefix):])
        else:
            return PackageVersion(version)
    except ValueError:
        pass
    return None


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
        result = PackageVersion(item)
        if fields:
            values = [result]
            for field in fields:
                values.append(item[field])
            result = tuple(values)
        return result

    try:
        return sorted(sortable, key=_version_sort_key, **kwargs)
    except (ValueError) as e:
        console_write(
            '''
            Error sorting versions - %s
            ''',
            e
        )
        return []
