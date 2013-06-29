"""pysemver: Semantic Version comparing for Python.

Provides comparing of semantic versions by using SemVer objects using rich comperations plus the
possibility to match a selector string against versions. Interesting for version dependencies.
Versions look like: "1.7.12+b.133"
Selectors look like: ">1.7.0 || 1.6.9+b.111 - 1.6.9+b.113"

Example usages:
    >>> SemVer(1, 2, 3, build=13)
    SemVer("1.2.3+13")
    >>> SemVer.valid("1.2.3.4")
    False
    >>> SemVer.clean("this is unimportant text 1.2.3-2 and will be stripped")
    "1.2.3-2"
    >>> SemVer("1.7.12+b.133").satisfies(">1.7.0 || 1.6.9+b.111 - 1.6.9+b.113")
    True
    >>> SemSel(">1.7.0 || 1.6.9+b.111 - 1.6.9+b.113").matches(SemVer("1.7.12+b.133"),
    ... SemVer("1.6.9+b.112"), SemVer("1.6.10"))
    [SemVer("1.7.12+b.133"), SemVer("1.6.9+b.112")]
    >>> min(_)
    SemVer("1.6.9+b.112")
    >>> _.patch
    9

Exported classes:
    * SemVer(collections.namedtuple())
        Parses semantic versions and defines methods for them. Supports rich comparisons.
    * SemSel(tuple)
        Parses semantic version selector strings and defines methods for them.
    * SelParseError(Exception)
        An error among others raised when parsing a semantic version selector failed.

Other classes:
    * SemComparator(object)
    * SemSelAndChunk(list)
    * SemSelOrChunk(list)

Functions/Variables/Constants:
    none


Copyright (c) 2013 Zachary King, FichteFoll

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions: The above copyright notice and this
permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import re
import sys
from collections import namedtuple  # Python >=2.6


__all__ = ('SemVer', 'SemSel', 'SelParseError')


if sys.version_info[0] == 3:
    basestring = str
    cmp = lambda a, b: (a > b) - (a < b)


# @functools.total_ordering would be nice here but was added in 2.7, __cmp__ is not Py3
class SemVer(namedtuple("_SemVer", 'major, minor, patch, prerelease, build')):
    """Semantic Version, consists of 3 to 5 components defining the version's adicity.

    See http://semver.org/ (2.0.0-rc.1) for the standard mainly used for this implementation, few
    changes have been made.

    Information on this particular class and their instances:
        - Immutable and hashable.
        - Subclasses `collections.namedtuple`.
        - Always `True` in boolean context.
        - len() returns an int between 3 and 5; 4 when a pre-release is set and 5 when a build is
          set. Note: Still returns 5 when build is set but not pre-release.
        - Parts of the semantic version can be accessed by integer indexing, key (string) indexing,
          slicing and getting an attribute. Returned slices are tuple. Leading '-' and '+' of
          optional components are not stripped. Supported keys/attributes:
          major, minor, patch, prerelease, build.

          Examples:
            s = SemVer("1.2.3-4.5+6")
            s[2] == 3
            s[:3] == (1, 2, 3)
            s['build'] == '-4.5'
            s.major == 1

    Short information on semantic version structure:

    Semantic versions consist of:
        * a major component (numeric)
        * a minor component (numeric)
        * a patch component (numeric)
        * a pre-release component [optional]
        * a build component [optional]

    The pre-release component is indicated by a hyphen '-' and followed by alphanumeric[1] sequences
    separated by dots '.'. Sequences are compared numerically if applicable (both sequences of two
    versions are numeric) or lexicographically. May also include hyphens. The existence of a
    pre-release component lowers the actual version; the shorter pre-release component is considered
    lower. An 'empty' pre-release component is considered to be the least version for this
    major-minor-patch combination (e.g. "1.0.0-").

    The build component may follow the optional pre-release component and is indicated by a plus '+'
    followed by sequences, just as the pre-release component. Comparing works similarly. However the
    existence of a build component raises the actual version and may also raise a pre-release. An
    'empty' build component is considered to be the highest version for this
    major-minor-patch-prerelease combination (e.g. "1.2.3+").


    [1]: Regexp for a sequence: r'[0-9A-Za-z-]+'.
    """

    # Static class variables
    _base_regex = r'''(?x)
        (?P<major>[0-9]+)
        \.(?P<minor>[0-9]+)
        \.(?P<patch>[0-9]+)
        (?:\-(?P<prerelease>(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?))?
        (?:\+(?P<build>(?:[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?))?'''
    _search_regex = re.compile(_base_regex)
    _match_regex  = re.compile('^%s$' % _base_regex)  # required because of $ anchor

    # "Constructor"
    def __new__(cls, *args, **kwargs):
        """There are two different constructor styles that are allowed:
        - Option 1 allows specification of a semantic version as a string and the option to "clean"
          the string before parsing it.
        - Option 2 allows specification of each component separately as one parameter.

        Note that all the parameters specified in the following sections can be passed either as
        positional or as named parameters while considering the usual Python rules for this. As
        such, `SemVer(1, 2, minor=1)` will result in an exception and not in `SemVer("1.1.2")`.

        Option 1:
            Constructor examples:
                SemVer("1.0.1")
                SemVer("this version 1.0.1-pre.1 here", True)
                SemVer(ver="0.0.9-pre-alpha+34", clean=False)

            Parameters:
                * ver (str)
                    The string containing the version.
                * clean = `False` (bool; optional)
                    If this is true in boolean context, `SemVer.clean(ver)` is called before
                    parsing.

        Option 2:
            Constructor examples:
                SemVer(1, 0, 1)
                SemVer(1, '0', prerelease='pre-alpha', patch=1, build=34)
                SemVer(**dict(minor=2, major=1, patch=3))

            Parameters:
                * major (int, str, float ...)
                * minor (...)
                * patch (...)
                    Major to patch components must be an integer or convertable to an int (e.g. a
                    string or another number type).

                * prerelease = `None` (str, int, float ...; optional)
                * build = `None` (...; optional)
                    Pre-release and build components should be a string (or number) type.
                    Will be passed to `str()` if not already a string but the final string must
                    match '^[0-9A-Za-z.-]*$'

        Raises:
            * TypeError
                Invalid parameter type(s) or combination (e.g. option 1 and 2).
            * ValueError
                Invalid semantic version or option 2 parameters unconvertable.
        """
        ver, clean, comps = None, False, None
        kw, l = kwargs.copy(), len(args) + len(kwargs)

        def inv():
            raise TypeError("Invalid parameter combination: args=%s; kwargs=%s" % (args, kwargs))

        # Do validation and parse the parameters
        if l == 0 or l > 5:
            raise TypeError("SemVer accepts at least 1 and at most 5 arguments (%d given)" % l)

        elif l < 3:
            if len(args) == 2:
                ver, clean = args
            else:
                ver = args[0] if args else kw.pop('ver', None)
                clean = kw.pop('clean', clean)
                if kw:
                    inv()

        else:
            comps = list(args) + [kw.pop(cls._fields[k], None) for k in range(len(args), 5)]
            if kw or any(comps[i] is None for i in range(3)):
                inv()

            typecheck = (int,) * 3 + (basestring,) * 2
            for i, (v, t) in enumerate(zip(comps, typecheck)):
                if v is None:
                    continue
                elif not isinstance(v, t):
                    try:
                        if i < 3:
                            v = typecheck[i](v)
                        else:  # The real `basestring` can not be instatiated (Py2)
                            v = str(v)
                    except ValueError as e:
                        # Modify the exception message. I can't believe this actually works
                        e.args = ("Parameter #%d must be of type %s or convertable"
                                  % (i, t.__name__),)
                        raise
                    else:
                        comps[i] = v
                if t is basestring and not re.match(r"^[0-9A-Za-z.-]*$", v):
                    raise ValueError("Build and pre-release strings must match '^[0-9A-Za-z.-]*$'")

        # Final adjustments
        if not comps:
            if ver is None or clean is None:
                inv()
            ver = clean and cls.clean(ver) or ver
            comps = cls._parse(ver)

        # Create the obj
        return super(SemVer, cls).__new__(cls, *comps)

    # Magic methods
    def __str__(self):
        return ('.'.join(map(str, self[:3]))
                + ('-' + self.prerelease if self.prerelease is not None else '')
                + ('+' + self.build if self.build is not None else ''))

    def __repr__(self):
        # Use the shortest representation - what would you prefer?
        return 'SemVer("%s")' % str(self)
        # return 'SemVer(%s)' % ', '.join('%s=%r' % (k, getattr(self, k)) for k in self._fields)

    def __len__(self):
        return 3 + (self.build is not None and 2 or self.prerelease is not None)

    # Magic rich comparing methods
    def __gt__(self, other):
        return self._compare(other) == 1 if isinstance(other, SemVer) else NotImplemented

    def __eq__(self, other):
        return self._compare(other) == 0 if isinstance(other, SemVer) else NotImplemented

    def __lt__(self, other):
        return not (self > other or self == other)

    def __ge__(self, other):
        return not (self < other)

    def __le__(self, other):
        return not (self > other)

    def __ne__(self, other):
        return not (self == other)

    # Utility (class-)methods
    def satisfies(self, sel):
        """Alias for `bool(sel.matches(self))` or `bool(SemSel(sel).matches(self))`.

        See `SemSel.__init__()` and `SemSel.matches(*vers)` for possible exceptions.

        Returns:
            * bool: `True` if the version matches the passed selector, `False` otherwise.
        """
        if not isinstance(sel, SemSel):
            sel = SemSel(sel)  # just "re-raise" exceptions

        return bool(sel.matches(self))

    @classmethod
    def valid(cls, ver):
        """Check if `ver` is a valid semantic version. Classmethod.

        Parameters:
            * ver (str)
                The string that should be stripped.

        Raises:
            * TypeError
                Invalid parameter type.

        Returns:
            * bool: `True` if it is valid, `False` otherwise.
        """
        if not isinstance(ver, basestring):
            raise TypeError("%r is not a string" % ver)

        if cls._match_regex.match(ver):
            return True
        else:
            return False

    @classmethod
    def clean(cls, vers):
        """Remove everything before and after a valid version string. Classmethod.

        Parameters:
            * vers (str)
                The string that should be stripped.

        Raises:
            * TypeError
                Invalid parameter type.

        Returns:
            * str:  The stripped version string. Only the first version is matched.
            * None: No version found in the string.
        """
        if not isinstance(vers, basestring):
            raise TypeError("%r is not a string" % vers)
        m = cls._search_regex.search(vers)
        if m:
            return vers[m.start():m.end()]
        else:
            return None

    # Private (class-)methods
    @classmethod
    def _parse(cls, ver):
        """Private. Do not touch. Classmethod.
        """
        if not isinstance(ver, basestring):
            raise TypeError("%r is not a string" % ver)

        match = cls._match_regex.match(ver)

        if match is None:
            raise ValueError("'%s' is not a valid SemVer string" % ver)

        g = list(match.groups())
        for i in range(3):
            g[i] = int(g[i])

        return g  # Will be passed as namedtuple(...)(*g)

    def _compare(self, other):
        """Private. Do not touch.
        self > other: 1
        self = other: 0
        self < other: -1
        """
        # Shorthand lambdas
        cp_len = lambda t, i=0: cmp(len(t[i]), len(t[not i]))

        for i, (x1, x2) in enumerate(zip(self, other)):
            if i > 2:
                if x1 is None and x2 is None:
                    continue

                # self is greater when other has a prerelease but self doesn't
                # self is less    when other has a build      but self doesn't
                if x1 is None or x2 is None:
                    return int(2 * (i - 3.5)) * (1 - 2 * (x1 is None))

                # self is less when other's build is empty
                if i == 4 and (not x1 or not x2) and x1 != x2:
                    return 1 - 2 * bool(x1)

                # Split by '.' and use numeric comp or lexicographical order
                t2 = [x1.split('.'), x2.split('.')]
                for y1, y2 in zip(*t2):
                    if y1.isdigit() and y2.isdigit():
                        y1 = int(y1)
                        y2 = int(y2)
                    if y1 > y2:
                        return 1
                    elif y1 < y2:
                        return -1

                # The "longer" sub-version is greater
                d = cp_len(t2)
                if d:
                    return d
            else:
                if x1 > x2:
                    return 1
                elif x1 < x2:
                    return -1

        # The versions equal
        return 0


class SemComparator(object):
    """Holds a SemVer object and a comparing operator and can match these against a given version.

    Constructor: SemComparator('<=', SemVer("1.2.3"))

    Methods:
        * matches(ver)
    """
    # Private properties
    _ops = {
        '>=': '__ge__',
        '<=': '__le__',
        '>':  '__gt__',
        '<':  '__lt__',
        '=':  '__eq__',
        '!=': '__ne__'
    }
    _ops_satisfy = ('~', '!')

    # Constructor
    def __init__(self, op, ver):
        """Constructor examples:
        SemComparator('<=', SemVer("1.2.3"))
        SemComparator('!=', SemVer("2.3.4"))

        Parameters:
            * op (str, False, None)
                One of [>=, <=, >, <, =, !=, !, ~] or evaluates to `False` which defaults to '~'.
                '~' means a "satisfy" operation where pre-releases and builds are ignored.
                '!' is a negative "~".
            * ver (SemVer)
                Holds the version to compare with.

        Raises:
            * ValueError
                Invalid `op` parameter.
            * TypeError
                Invalid `ver` parameter.
        """
        super(SemComparator, self).__init__()

        if op and op not in self._ops_satisfy and op not in self._ops:
            raise ValueError("Invalid value for `op` parameter.")
        if not isinstance(ver, SemVer):
            raise TypeError("`ver` parameter is not instance of SemVer.")

        # Default to '~' for versions with no build or pre-release
        op = op or '~'
        # Fallback to '=' and '!=' if len > 3
        if len(ver) != 3:
            if op == '~':
                op = '='
            if op == '!':
                op = '!='

        self.op  = op
        self.ver = ver

    # Magic methods
    def __str__(self):
        return (self.op or "") + str(self.ver)

    # Utility methods
    def matches(self, ver):
        """Match the internal version (constructor) against `ver`.

        Parameters:
            * ver (SemVer)

        Raises:
            * TypeError
                Could not compare `ver` against the version passed in the constructor with the
                passed operator.

        Returns:
            * bool
                `True` if the version matched the specified operator and internal version, `False`
                otherwise.
        """
        if self.op in self._ops_satisfy:
            # Compare only the first three parts (which are tuples) and directly
            return bool((self.ver[:3] == ver[:3]) + (self.op == '!') * -1)
        ret = getattr(ver, self._ops[self.op])(self.ver)
        if ret == NotImplemented:
            raise TypeError("Unable to compare %r with operator '%s'" % (ver, self.op))
        return ret


class SemSelAndChunk(list):
    """Extends list and defines a few methods used for matching versions.

    New elements should be added by calling `.add_child(op, ver)` which creates a SemComparator
    instance and adds that to itself.

    Methods:
        * matches(ver)
        * add_child(op, ver)
    """
    # Magic methods
    def __str__(self):
        return ' '.join(map(str, self))

    # Utitlity methods
    def matches(self, ver):
        """Match all of the added children against `ver`.

        Parameters:
            * ver (SemVer)

        Raises:
            * TypeError
                Invalid `ver` parameter.

        Returns:
            * bool:
                `True` if *all* of the SemComparator children match `ver`, `False` otherwise.
        """
        if not isinstance(ver, SemVer):
            raise TypeError("`ver` parameter is not instance of SemVer.")
        return all(cp.matches(ver) for cp in self)

    def add_child(self, op, ver):
        """Create a SemComparator instance with the given parameters and appends that to self.

        Parameters:
            * op (str)
            * ver (SemVer)
        Both parameters are forwarded to `SemComparator.__init__`, see there for a more detailed
        description.

        Raises:
            Exceptions raised by `SemComparator.__init__`.
        """
        self.append(SemComparator(op, SemVer(ver)))


class SemSelOrChunk(list):
    """Extends list and defines a few methods used for matching versions.

    New elements should be added by calling `.new_child()` which returns a SemSelAndChunk
    instance.

    Methods:
        * matches(ver)
        * new_child()
    """
    # Magic methods
    def __str__(self):
        return ' || '.join(map(str, self))

    # Utility methods
    def matches(self, ver):
        """Match all of the added children against `ver`.

        Parameters:
            * ver (SemVer)

        Raises:
            * TypeError
                Invalid `ver` parameter.

        Returns:
            * bool
                `True` if *any* of the SemSelAndChunk children matches `ver`.
                `False` otherwise.
        """
        if not isinstance(ver, SemVer):
            raise TypeError("`ver` parameter is not instance of SemVer.")
        return any(ch.matches(ver) for ch in self)

    def new_child(self):
        """Creates a new SemSelAndChunk instance, appends it to self and returns it.

        Returns:
            * SemSelAndChunk: An empty instance.
        """
        ch = SemSelAndChunk()
        self.append(ch)
        return ch


class SelParseError(Exception):
    """An Exception raised when parsing a semantic selector failed.
    """
    pass


# Subclass `tuple` because this is a somewhat simple method to make this immutable
class SemSel(tuple):
    """A Semantic Version Selector, holds a selector and can match it against semantic versions.

    Information on this particular class and their instances:
        - Immutable but not hashable because the content within might have changed.
        - Subclasses `tuple` but does not behave like one.
        - Always `True` in boolean context.
        - len() returns the number of containing *and chunks* (see below).
        - Iterable, iterates over containing *and chunks*.

    When talking about "versions" it refers to a semantic version (SemVer). For information on how
    versions compare to one another, see SemVer's doc string.

    List for **comparators**:
        "1.0.0"            matches the version 1.0.0 and all its pre-release and build variants
        "!1.0.0"           matches any version that is not 1.0.0 or any of its variants
        "=1.0.0"           matches only the version 1.0.0
        "!=1.0.0"          matches any version that is not 1.0.0
        ">=1.0.0"          matches versions greater than or equal 1.0.0
        "<1.0.0"           matches versions smaller than 1.0.0
        "1.0.0 - 1.0.3"    matches versions greater than or equal 1.0.0 thru 1.0.3
        "~1.0"             matches versions greater than or equal 1.0.0 thru 1.0.9999 (and more)
        "~1", "1.x", "1.*" match versions greater than or equal 1.0.0 thru 1.9999.9999 (and more)
        "~1.1.2"           matches versions greater than or equal 1.1.2 thru 1.1.9999 (and more)
        "~1.1.2+any"       matches versions greater than or equal 1.1.2+any thru 1.1.9999 (and more)
        "*", "~", "~x"     match any version

    Multiple comparators can be combined by using ' ' spaces and every comparator must match to make
    the **and chunk** match a version.
    Multiple and chunks can be combined to **or chunks** using ' || ' and match if any of the and
    chunks split by these matches.

    A complete example would look like:
        ~1 || 0.0.3 || <0.0.2 >0.0.1+b.1337 || 2.0.x || 2.1.0 - 2.1.0+b.12 !=2.1.0+b.9

    Methods:
        * matches(*vers)
    """
    # Private properties
    _fuzzy_regex = re.compile(r'''(?x)^
        (?P<op>[<>]=?|~>?=?)?
        (?:(?P<major>\d+)
         (?:\.(?P<minor>\d+)
          (?:\.(?P<patch>\d+)
           (?P<other>[-+][a-zA-Z0-9-+.]*)?
          )?
         )?
        )?$''')
    _xrange_regex = re.compile(r'''(?x)^
        (?P<op>[<>]=?|~>?=?)?
        (?:(?P<major>\d+|[xX*])
         (?:\.(?P<minor>\d+|[xX*])
          (?:\.(?P<patch>\d+|[xX*]))?
         )?
        )
        (?P<other>.*)$''')
    _split_op_regex = re.compile(r'^(?P<op>=|[<>!]=?)?(?P<ver>.*)$')

    # "Constructor"
    def __new__(cls, sel):
        """Constructor examples:
            SemSel(">1.0.0")
            SemSel("~1.2.9 !=1.2.12")

        Parameters:
            * sel (str)
                A version selector string.

        Raises:
            * TypeError
                `sel` parameter is not a string.
            * ValueError
                A version in the selector could not be matched as a SemVer.
            * SemParseError
                The version selector's syntax is unparsable; invalid ranges (fuzzy, xrange or
                explicit range) or invalid '||'
        """
        chunk = cls._parse(sel)
        return super(SemSel, cls).__new__(cls, (chunk,))

    # Magic methods
    def __str__(self):
        return str(self._chunk)

    def __repr__(self):
        return 'SemSel("%s")' % self._chunk

    def __len__(self):
        # What would you expect?
        return len(self._chunk)

    def __iter__(self):
        return iter(self._chunk)

    # Read-only (private) attributes
    @property
    def _chunk(self):
        return self[0]

    # Utility methods
    def matches(self, *vers):
        """Match the selector against a selection of versions.

        Parameters:
            * *vers (str, SemVer)
                Versions can be passed as strings and SemVer objects will be created with them.
                May also be a mixed list.

        Raises:
            * TypeError
                A version is not an instance of str (basestring) or SemVer.
            * ValueError
                A string version could not be parsed as a SemVer.

        Returns:
            * list
                A list with all the versions that matched, may be empty. Use `max()` to determine
                the highest matching version, or `min()` for the lowest.
        """
        ret = []
        for v in vers:
            if isinstance(v, str):
                t = self._chunk.matches(SemVer(v))
            elif isinstance(v, SemVer):
                t = self._chunk.matches(v)
            else:
                raise TypeError("Invalid parameter type '%s': %s" % (v, type(v)))
            if t:
                ret.append(v)

        return ret

    # Private methods
    @classmethod
    def _parse(cls, sel):
        """Private. Do not touch.

        1. split by whitespace into tokens
            a. start new and_chunk on ' || '
            b. parse " - " ranges
            c. replace "xX*" ranges with "~" equivalent
            d. parse "~" ranges
            e. parse unmatched token as comparator
            ~. append to current and_chunk
        2. return SemSelOrChunk

        Raises TypeError, ValueError or SelParseError.
        """
        if not isinstance(sel, basestring):
            raise TypeError("Selector must be a string")
        if not sel:
            raise ValueError("String must not be empty")

        # Split selector by spaces and crawl the tokens
        tokens = sel.split()
        i = -1
        or_chunk = SemSelOrChunk()
        and_chunk = or_chunk.new_child()

        while i + 1 < len(tokens):
            i += 1
            t = tokens[i]

            # Replace x ranges with ~ selector
            m = cls._xrange_regex.match(t)
            m = m and m.groups('')
            if m and any(not x.isdigit() for x in m[1:4]) and not m[0].startswith('>'):
                # (do not match '>1.0' or '>*')
                if m[4]:
                    raise SelParseError("XRanges do not allow pre-release or build components")

                # Only use digit parts and fail if digit found after non-digit
                mm, xran = [], False
                for x in m[1:4]:
                    if x.isdigit():
                        if xran:
                            raise SelParseError("Invalid fuzzy range or XRange '%s'" % tokens[i])
                        mm.append(x)
                    else:
                        xran = True
                t = m[0] + '.'.join(mm)  # x for x in m[1:4] if x.isdigit())
                # Append "~" if not already present
                if not t.startswith('~'):
                    t = '~' + t

            # switch t:
            if t == '||':
                if i == 0 or tokens[i - 1] == '||' or i + 1 == len(tokens):
                    raise SelParseError("OR range must not be empty")
                # Start a new and_chunk
                and_chunk = or_chunk.new_child()

            elif t == '-':
                # ' - ' range
                i += 1
                invalid = False
                try:
                    # If these result in exceptions, you know you're doing it wrong
                    t = tokens[i]
                    c = and_chunk[-1]
                except:
                    raise SelParseError("Invalid ' - ' range position")

                # If there is an op in front of one of the bound versions
                invalid = (c.op not in ('=', '~')
                           or cls._split_op_regex.match(t).group(1) not in (None, '='))
                if invalid:
                    raise SelParseError("Invalid ' - ' range '%s - %s'"
                                        % (tokens[i - 2], tokens[i]))

                c.op = ">="
                and_chunk.add_child('<=', t)

            elif t == '':
                # Multiple spaces
                pass

            elif t.startswith('~'):
                m = cls._fuzzy_regex.match(t)
                if not m:
                    raise SelParseError("Invalid fuzzy range or XRange '%s'" % tokens[i])

                mm, m = m.groups('')[1:4], m.groupdict('')  # mm: major to patch

                # Minimum requirement
                min_ver = ('.'.join(x or '0' for x in mm) + '-'
                           if not m['other']
                           else cls._split_op_regex(t[1:]).group('ver'))
                and_chunk.add_child('>=', min_ver)

                if m['major']:
                    # Increase version before none (or second to last if '~1.2.3')
                    e = [0, 0, 0]
                    for j, d in enumerate(mm):
                        if not d or j == len(mm) - 1:
                            e[j - 1] = e[j - 1] + 1
                            break
                        e[j] = int(d)

                    and_chunk.add_child('<', '.'.join(str(x) for x in e) + '-')

                # else: just plain '~' or '*', or '~>X' which are already handled

            else:
                # A normal comparator
                m = cls._split_op_regex.match(t).groupdict()  # this regex can't fail
                and_chunk.add_child(**m)

        # Finally return the or_chunk
        return or_chunk