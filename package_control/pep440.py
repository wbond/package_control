"""
A PEP440 complient version module for use by Package Control.

Note:

This module implements ``PEP440Version`` and ``PEP440VersionSpecifier``
using independent implementations and regex patterns to parse their string
representation, even though both share a lot.

The reason for this kind of inlining is targetting best possible performance
for creating and compairing versions, rather than strictly following a
questionable DRY approach.

Instantiation for each object consists of only 2 main steps:

1. parse and validate input string using a single regular expression.
2. convert match groups into nested tuple representation, as primary
   data storage and comparing key.

The patterns include additional pre-release tag names
(e.g: ``patch``, ``prerelease``, ``developmment``, ``test``)
to maintain compatibility with various existing packages on packagecontrol.io
"""
import re

__all__ = [
    "PEP440InvalidVersionError",
    "PEP440InvalidVersionSpecifierError",
    "PEP440Version",
    "PEP440VersionSpecifier",
    "check_version"
]

_local_version_separators = re.compile(r"[-._]")


def _norm_tuples(a, b):
    """
    Accepts two tuples of PEP440 version numbers and extends them until they
    are the same length. This allows for comparisons between them.

    Notes:

    - prerelease segment is padded
    - local version don't need padding as shorter sort before longer

    :param a:
        A tuple from ``PEP440Version``
        of the format: ``(epoch, release, prerelease, local)``

    :param b:
        A tuple from ``PEP440Version``
        of the format: ``(epoch, release, prerelease, local)``

    :return:
        Two potentially modified tuples, (a, b)
    """
    # pad release
    ar = a[1]
    br = b[1]

    arl = len(ar)
    brl = len(br)

    if arl < brl:
        while len(ar) < brl:
            ar += (0,)
        a = a[:1] + (ar,) + a[2:]

    elif arl > brl:
        while arl > len(br):
            br += (0,)
        b = b[:1] + (br,) + b[2:]

    return a, b


def _trim_tuples(spec, ver):
    """
    Trim version to match specification's length.

    :param spec:
        A tuple from ``PEP440VersionSpecifier``, representing a version prefix.
        e.g.: ``(epoch, (major [, minor [, micro] ] ) )``

    :param ver:
        A tuple from ``PEP440Version``

    :returns:
        A tuple of prefix and trimmed version.
    """
    segs = len(spec[1])
    release = ver[1][:segs]
    while len(release) < segs:
        release += (0,)
    return spec, (ver[0], release)


def _version_info(epoch, ver, pre, local, verbose=False):
    """
    Create a ``__version_info__`` tuple representation.

    :param epoch:
        The epoch

    :param ver:
        A tuple of integers representing the version

    :param pre:
        A tuple of tuples of integers representing pre-releases

    :param local:
        Local version representation.

    :returns:
        A tuple of (major, minor, micro, 'pre', 'post', 'dev')
    """
    info = ver

    if pre and pre[0][0] != 0:
        if verbose:
            tag = ("dev", "alpha", "beta", "rc", "", "post")
        else:
            tag = ("dev", "a", "b", "rc", "", "post")
        for t, n in pre:
            if t != 0:
                info += (tag[t + 4], n)
    else:
        info += ("final",)

    if local:
        info += (".".join(str(n) if n > -1 else s for n, s in local),)

    return info


def _version_string(epoch, ver, pre, local, prefix=False, verbose=False):
    """
    Create a normalized string representation.

    :param epoch:
        The epoch

    :param ver:
        A tuple of integers representing the version

    :param pre:
        A tuple of tuples of integers representing pre-releases

    :param local:
        Local version representation.

    :returns:
        String representation of the version.
    """
    string = str(epoch) + "!" if epoch else ""
    string += ".".join(map(str, ver))

    if prefix:
        return string + ".*"

    if pre and pre[0][0] != 0:
        if verbose:
            tag = ("-dev{}", "-alpha{}", "-beta{}", "-rc{}", "", "-post{}")
        else:
            tag = (".dev{}", "a{}", "b{}", "rc{}", "", ".post{}")
        for t, n in pre:
            if t != 0:
                string += tag[t + 4].format(n)

    if local:
        string += "+" + ".".join(str(n) if n > -1 else s for n, s in local)

    return string


class PEP440InvalidVersionError(ValueError):
    pass


class PEP440Version:
    __slots__ = ["_tup"]

    _regex = re.compile(
        r"""
        ^\s*
        v?
        (?:(?P<epoch>[0-9]+)!)?                               # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*)                      # release segment
        (?P<pre>                                              # pre-release
            [-_.]?
            (?P<pre_l>alpha|a|beta|b|prerelease|preview|pre|c|rc)
            [-_.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>                                             # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_.]?
                (?P<post_l>patch|post|rev|r)
                [-_.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>                                              # dev release
            [-_.]?
            (?P<dev_l>development|develop|devel|dev)
            [-_.]?
            (?P<dev_n>[0-9]+)?
        )?
        (?:\+(?P<local>[a-z0-9]+(?:[-_.][a-z0-9]+)*))?        # local version
        \s*$
        """,
        re.VERBOSE,
    )

    def __init__(self, string):
        """
        Constructs a new ``PEP440Version`` instance.

        :param string:
            An unicode string of the pep44ß version.
        """
        match = self._regex.match(string.lower())
        if not match:
            raise PEP440InvalidVersionError("'{}' is not a valid PEP440 version string".format(string))

        (
            epoch,
            release,
            pre,
            pre_l,
            pre_n,
            post,
            post_n1,
            _,
            post_n2,
            dev,
            _,
            dev_n,
            local,
        ) = match.groups()

        epoch = int(epoch or 0)
        release = tuple(map(int, release.split(".")))

        prerelease = ()

        if pre:
            if pre_l == "a" or pre_l == "alpha":
                pre_l = -3
            elif pre_l == "b" or pre_l == "beta":
                pre_l = -2
            else:
                pre_l = -1
            prerelease += ((pre_l, int(pre_n or 0)),)

        if post:
            prerelease += ((1, int(post_n1 or post_n2 or 0)),)

        if dev:
            prerelease += ((-4, int(dev_n or 0)),)

        while len(prerelease) < 3:
            prerelease += ((0, 0),)

        tup = ()
        if local:
            # Versions with a local segment need that segment parsed to implement
            # the sorting rules in PEP440.
            # - Alpha numeric segments sort before numeric segments
            # - Alpha numeric segments sort lexicographically
            # - Numeric segments sort numerically
            # - Shorter versions sort before longer versions when the prefixes
            #   match exactly
            for seg in _local_version_separators.split(local):
                try:
                    tup += ((int(seg), ""),)
                except ValueError:
                    tup += ((-1, seg),)

        local = tup

        self._tup = (epoch, release, prerelease, local)

    def __repr__(self):
        return "<{0.__class__.__name__}('{0!s}')>".format(self)

    def __str__(self):
        return self.version_string()

    def __eq__(self, rhs):
        a, b = _norm_tuples(self._tup, rhs._tup)
        return a == b

    def __ne__(self, rhs):
        a, b = _norm_tuples(self._tup, rhs._tup)
        return a != b

    def __lt__(self, rhs):
        a, b = _norm_tuples(self._tup, rhs._tup)
        return a < b

    def __le__(self, rhs):
        a, b = _norm_tuples(self._tup, rhs._tup)
        return a <= b

    def __gt__(self, rhs):
        a, b = _norm_tuples(self._tup, rhs._tup)
        return a > b

    def __ge__(self, rhs):
        a, b = _norm_tuples(self._tup, rhs._tup)
        return a >= b

    def __hash__(self):
        return hash(self._tup)

    def version_info(self, verbose=False):
        return _version_info(*self._tup, verbose=verbose)

    def version_string(self, verbose=False):
        return _version_string(*self._tup, verbose=verbose)

    @property
    def epoch(self):
        return self._tup[0]

    @property
    def release(self):
        return self._tup[1]

    @property
    def major(self):
        try:
            return self._tup[1][0]
        except IndexError:
            return 0

    @property
    def minor(self):
        try:
            return self._tup[1][1]
        except IndexError:
            return 0

    @property
    def micro(self):
        try:
            return self._tup[1][2]
        except IndexError:
            return 0

    @property
    def prerelease(self):
        tup = ()
        pre = self._tup[2]
        if pre and pre[0][0] != 0:
            tag = ("dev", "a", "b", "rc", "", "post")
            for t, n in pre:
                if t != 0:
                    tup += (tag[t + 4], n)

        return tup

    @property
    def local(self):
        return ".".join(str(n) if n > -1 else s for n, s in self._tup[3])

    @property
    def is_final(self):
        """Version represents a final release."""
        return self._tup[2][0][0] == 0

    @property
    def is_dev(self):
        """Version represents a pre release."""
        return any(t[0] == -4 for t in self._tup[2])

    @property
    def is_prerelease(self):
        """Version represents a pre release."""
        return self._tup[2][0][0] < 0

    @property
    def is_postrelease(self):
        """Version represents a post final release."""
        return self._tup[2][0][0] > 0


class PEP440InvalidVersionSpecifierError(ValueError):
    pass


class PEP440VersionSpecifier:
    __slots__ = ["_operator", "_prefix", "_prereleases", "_tup"]

    _regex = re.compile(
        r"""
        ^\s*
        (?: (?P<op>===|==|!=|~=|<=?|>=?) \s* )?                 # operator
        v?
        (?:(?P<epoch>[0-9]+)!)?                             # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*)                    # release segment
        (?:
            \.(?P<wildcard>\*)                              # prefix-release
            |
            (?P<pre>                                        # pre-release
                [-_.]?
                (?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)
                [-_.]?
                (?P<pre_n>[0-9]+)?
            )?
            (?P<post>                                       # post release
                (?:-(?P<post_n1>[0-9]+))
                |
                (?:
                    [-_.]?
                    (?P<post_l>post|rev|r)
                    [-_.]?
                    (?P<post_n2>[0-9]+)?
                )
            )?
            (?P<dev>                                        # dev release
                [-_.]?
                (?P<dev_l>dev)
                [-_.]?
                (?P<dev_n>[0-9]+)?
            )?
            (?:\+(?P<local>[a-z0-9]+(?:[-_.][a-z0-9]+)*))?  # local version
        )
        \s*$
        """,
        re.VERBOSE,
    )

    _op_str = ("", "===", "==", "!=", "~=", "<", "<=", ">", ">=")

    OP_ITY = 1
    OP_EQ = 2
    OP_NE = 3
    OP_CPE = 4
    OP_LT = 5
    OP_LTE = 6
    OP_GT = 7
    OP_GTE = 8

    def __init__(self, string, prereleases=True):
        """
        Constructs a new ``PEP440VersionSpecifier`` instance.

        :param string:
            An unicode string of the pep44ß version specifier.
        """
        match = self._regex.match(string.lower())
        if not match:
            raise PEP440InvalidVersionSpecifierError(
                "'{}' is not a valid PEP 440 version specifier string".format(string)
            )

        (
            op,
            epoch,
            release,
            wildcard,
            pre,
            pre_l,
            pre_n,
            post,
            post_n1,
            _,
            post_n2,
            dev,
            _,
            dev_n,
            local,
        ) = match.groups()

        self._operator = self._op_str.index(op) if op else self.OP_EQ
        self._prefix = bool(wildcard)
        self._prereleases = prereleases

        epoch = int(epoch or 0)
        release = tuple(map(int, release.split(".")))

        if self._prefix:
            if self._operator not in (self.OP_EQ, self.OP_NE):
                raise PEP440InvalidVersionSpecifierError(
                    "'{}' is not a valid PEP 440 version specifier string".format(string)
                )

            self._tup = (epoch, release)
            return

        if self._operator == self.OP_CPE and len(release) < 2:
            raise PEP440InvalidVersionSpecifierError(
                "'{}' is not a valid PEP 440 version specifier string".format(string)
            )

        prerelease = ()

        if pre:
            if pre_l == "a" or pre_l == "alpha":
                pre_l = -3
            elif pre_l == "b" or pre_l == "beta":
                pre_l = -2
            else:
                pre_l = -1
            prerelease += ((pre_l, int(pre_n or 0)),)

        if post:
            prerelease += ((1, int(post_n1 or post_n2 or 0)),)

        if dev:
            prerelease += ((-4, int(dev_n or 0)),)

        while len(prerelease) < 3:
            prerelease += ((0, 0),)

        tup = ()
        if local:
            if self._operator not in (self.OP_EQ, self.OP_NE, self.OP_ITY):
                raise PEP440InvalidVersionSpecifierError(
                    "'{}' is not a valid PEP 440 version specifier string".format(string)
                )

            for seg in _local_version_separators.split(local):
                try:
                    tup += ((int(seg), ""),)
                except ValueError:
                    tup += ((-1, seg),)
        local = tup

        self._tup = (epoch, release, prerelease, local)

    def __repr__(self):
        return "<{0.__class__.__name__}('{0!s}')>".format(self)

    def __str__(self):
        return self._op_str[self._operator] + self.version_string()

    def __contains__(self, version):
        return self.contains(version)

    def __hash__(self):
        return hash((self._operator, self._tup))

    def contains(self, version):
        """
        Ensures the version matches this specifier

        :param version:
            A ``PEP440Version`` object to check.

        :return:
            Returns ``True`` if ``version`` satisfies the ``specifier``.
        """
        if not self._prereleases and version.is_prerelease:
            return False

        if self._prefix:
            # The specifier is a version prefix (aka. wildcard present).
            # Trim and normalize version to ( epoch, ( major [, minor [, micro ] ] ) ),
            # so it matches exactly the specifier's length.

            self_tup, ver_tup = _trim_tuples(self._tup, version._tup)

            if self._operator == self.OP_EQ:
                return ver_tup == self._tup

            if self._operator == self.OP_NE:
                return ver_tup != self._tup

        else:
            if self._operator == self.OP_ITY:
                return version.version_string(False) == self.version_string(False)

            self_tup, ver_tup = _norm_tuples(self._tup, version._tup)

            if self._operator == self.OP_CPE:
                # Compatible releases have an equivalent combination of >= and ==.
                # That is that ~=2.2 is equivalent to >=2.2,==2.*.
                if ver_tup < self_tup:
                    return False

                # create prefix specifier with last digit removed.
                self_tup, ver_tup = _trim_tuples((self._tup[0], self._tup[1][:-1]), version._tup)
                return ver_tup == self_tup

            if self._operator == self.OP_EQ:
                return ver_tup == self_tup

            if self._operator == self.OP_NE:
                return ver_tup != self_tup

            if self._operator == self.OP_GTE:
                return ver_tup >= self_tup

            if self._operator == self.OP_GT:
                # TODO:
                #  - parse local version and include into comparison result
                #  - drop only invalid local versions
                return ver_tup[:2] > self_tup[:2]

            if self._operator == self.OP_LTE:
                return ver_tup <= self_tup

            if self._operator == self.OP_LT:
                # TODO:
                #  - parse local version and include into comparison result
                #  - drop only invalid local versions
                return ver_tup[:2] < self_tup[:2]

        raise PEP440InvalidVersionSpecifierError(
            "Invalid PEP 440 version specifier operator: {!r}".format(self._operator)
        )

    def filter(self, iterable):
        return filter(self.contains, iterable)

    def version_string(self, verbose=False):
        return _version_string(*self._tup, prefix=self._prefix, verbose=verbose)


def check_version(spec, version, include_prereleases=False):
    """
    Check if version satisfies specifications

    :param spec:
        The pep440 version specifier string.

    :param version:
        The pep440 version string or ``PEP440Version`` ojbect to check.

    :param include_prereleases:
        If ``True`` succeed also, if version is a pre-release.
        If ``False`` (default) succeed only, if version is a final release.

    :returns:
        Returns ``True`` if ``version`` satisfies the ``specifier``.
    """
    if isinstance(version, str):
        version = PEP440Version(version)
    return PEP440VersionSpecifier(spec, include_prereleases).contains(version)
