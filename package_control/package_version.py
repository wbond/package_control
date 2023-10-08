import re

from .console_write import console_write
from .pep440 import PEP440Version, PEP440InvalidVersionError


class PackageVersion(PEP440Version):
    __slots__ = ["_str"]

    _date_time_regex = re.compile(r"^\d{4}\.\d{2}\.\d{2}(?:\.\d{2}\.\d{2}\.\d{2})?$")

    def __init__(self, ver):
        """
        Initialize a ``PackageVersion`` instance.

        The initializer acts as compatibility layer to convert legacy version schemes
        into a ``PEP440Version``.

        If the version is based on a date, converts to 0.0.1+yyyy.mm.dd.hh.mm.ss.

        :param ver:
            A string, dict with 'version' key, or a SemVer object

        :raises:
            TypeError, if ver is not a ``str``.
            ValueError, if ver is no valid version string
        """

        if not isinstance(ver, str):
            raise TypeError("{!r} is not a string".format(ver))

        # Store original version string to maintain backward compatibility
        # with regards to not normalize it.
        # The one and only use case is to keep existing CI tests working without change.
        self._str = ver

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
        match = self._date_time_regex.match(ver)
        if match:
            ver = "0.0.1+" + ver

        try:
            super().__init__(ver)
        except PEP440InvalidVersionError:
            # maybe semver with incompatible pre-release tag
            # if, so treat it as dev build with local version
            if "-" in ver:
                ver, pre = ver.split("-", 1)
                if ver and pre:
                    super().__init__(ver + "-dev+" + pre)
                    return
            raise

    def __str__(self):
        return self._str


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
        if isinstance(item, dict):
            if "version" not in item:
                raise TypeError("%s is not a package or library release" % item)
            result = PackageVersion(item["version"])
            if fields:
                result = (result,)
                for field in fields:
                    result += (item[field],)
            return result

        return PackageVersion(item)

    try:
        return sorted(sortable, key=_version_sort_key, **kwargs)
    except ValueError as e:
        console_write(
            """
            Error sorting versions - %s
            """,
            e,
        )
        return []
