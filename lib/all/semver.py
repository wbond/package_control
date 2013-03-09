# Copyright 2013, Zachary King, FichteFoll and Will Bond
# Licensed under the MIT license

import re
import sys

if sys.version_info[0] == 3:
    basestring = str
    cmp = lambda a, b: (a > b) - (a < b)


class SemVer(object):

    # Static class variables
    base_regex = (r'([v=]+\s*)?'
                  r'(?P<major>[0-9]+)'
                  r'\.(?P<minor>[0-9]+)'
                  r'\.(?P<patch>[0-9]+)'
                  r'(\-(?P<prerelease>[0-9A-Za-z]+(\.[0-9A-Za-z]+)*))?'
                  r'(\+(?P<build>[0-9A-Za-z]+(\.[0-9A-Za-z]+)*))?')
    search_regex = re.compile(base_regex)
    match_regex  = re.compile('^%s$' % base_regex)  # required because of $ anchor

    # Instance variables
    _initialized = False

    # Magic methods
    def __init__(self, version=None, clean=False):
        super(SemVer, self).__init__()

        if version:
            if clean:
                version = self.__class__.clean(version) or version
            self.parse(version)

    def __str__(self):
        temp_str = str(self.major) + "." + str(self.minor) + "." + str(self.patch)
        if self.prerelease is not None:
            temp_str += "-" + str(self.prerelease)
        if self.build is not None:
            temp_str += "+" + str(self.build)
        return temp_str

    def __repr__(self):
        return 'SemVer("%s")' % str(self)

    def __iter__(self):
        if self._initialized is True:
            result = [self.major,
                    self.minor,
                    self.patch]
            if self.prerelease is not None:
                result.append(self.prerelease)
            if self.build is not None:
                result.append(self.build)
            return iter(result)
        else:
            return False

    def __bool__(self):
        return self._initialized

    # __bool__ is Py3
    __nonzero__ = __bool__

    # Magic comparing methods
    def __gt__(self, other):
        if isinstance(other, SemVer):
            if self._compare(other) == 1:
                return True
            else:
                return False
        else:
            return NotImplemented

    def __eq__(self, other):
        if isinstance(other, SemVer):
            if self._compare(other) == 0:
                return True
            else:
                return False
        else:
            return NotImplemented

    def __lt__(self, other):
        return not (self > other or self == other)

    def __ge__(self, other):
        return not (self < other)

    def __le__(self, other):
        return not (self > other)

    def __ne__(self, other):
        return not (self == other)

    # Utility functions
    def satisfies(self, comp_range):
        comp_range = comp_range.replace(" - ", "---")
        or_ranges = comp_range.split(" || ")  # Split sting into segments joined by OR
        or_comps = []
        for or_range in or_ranges:
            and_ranges = or_range.split(' ')
            and_comps = []
            for and_range in and_ranges:
                # The 1.x and 1.2.x styles are equivalent to the more
                # complex forms ~1 and ~1.2
                x_regex = '(\d+)(.\d+)?.x'
                x_match = re.match(x_regex, and_range)
                if x_match:
                    and_range = '~' + and_range.replace('.x', '')

                if and_range.find('---') != -1:
                    ge_version, le_version = and_range.split('---')
                    and_comps.append(['__ge__', ge_version])
                    and_comps.append(['__le__', le_version])

                elif len(and_range) > 0 and and_range[0] == '~':
                    version = and_range[1:]
                    
                    regex = (r'(?P<major>[0-9]+)'
                             r'(?P<minor>.[0-9]+)?'
                             r'(?P<patch>.[0-9]+)?')
                    match = re.match(regex, version)
                    ge_info = match.groupdict()
                    lt_info = {}

                    if not ge_info['minor']:
                        ge_info['minor'] = '.0'

                        ge_major = int(ge_info['major'])
                        lt_info['major'] = str(ge_major + 1)
                        lt_info['minor'] = '.0'

                    else:
                        lt_info['major'] = ge_info['major']
                        ge_minor = int(ge_info['minor'].replace('.', ''))
                        lt_info['minor'] = '.' + str(ge_minor + 1)

                    if not ge_info['patch']:
                        ge_info['patch'] = '.0'
                    
                    lt_info['patch'] = '.0'

                    ge_version = ge_info['major'] + ge_info['minor'] + ge_info['patch']
                    lt_version = lt_info['major'] + lt_info['minor'] + lt_info['patch']
                    and_comps.append(['__ge__', ge_version])
                    and_comps.append(['__lt__', lt_version])

                else:
                    op_match = re.match('(>=|<=|>|<)(.*)$', and_range)
                    if not op_match:
                        raise ValueError('%s is not a valid SemVer range' % comp_range)
                    
                    op, version = op_match.groups()
                    ops = {
                        '>=': '__ge__',
                        '<=': '__le__',
                        '>': '__gt__',
                        '<': '__lt__'
                    }
                    and_comps.append([ops[op], version])

            or_comps.append(and_comps)

        for or_comps in or_comps:
            and_comp_true = True
            for ands in or_comps:
                method = getattr(self, ands[0])
                version = SemVer(ands[1])
                and_comp_true = and_comp_true and method(version)
            if and_comp_true:
                return True

        return False

    @classmethod
    def valid(cls, version):
        if not isinstance(version, basestring):
            raise TypeError("%r is not a string" % version)

        if cls.match_regex.match(version):
            return True
        else:
            return False

    @classmethod
    def clean(cls, version):
        m = cls.search_regex.search(version)
        if m:
            return version[m.start():m.end()]
        else:
            return None

    def parse(self, version):
        if self._initialized:
            raise RuntimeError("SemVer instance has already been initialized with %s" % str(self))
        if not isinstance(version, basestring):
            raise TypeError("%r is not a string" % version)

        match = self.match_regex.match(version)

        if match is None:
            raise ValueError('%s is not a valid SemVer string' % version)

        info = match.groupdict()

        self.major = int(info['major'])
        self.minor = int(info['minor'])
        self.patch = int(info['patch'])

        if info['prerelease'] is not None:
            self.prerelease = info['prerelease']
        else:
            self.prerelease = None
        if info['build'] is not None:
            self.build = info['build']
        else:
            self.build = None

        self._initialized = True
        return True

    def _compare(self, other):
        # Because zip truncates to the shortest parameter list
        # this is required to make the longer list win
        cp_len = lambda t, i=0: cmp(len(t[i]), len(t[not i]))

        i = 0
        t1 = [tuple(self), tuple(other)]
        for x1, x2 in zip(*t1):
            if i > 2:
                # Use numeric comp or lexicographical order - split by '.' for tag and build
                t2 = [x1.split('.'), x2.split('.')]
                for y1, y2 in zip(*t2):
                    if y1.isdigit() and y2.isdigit():
                        y1 = int(y1)
                        y2 = int(y2)
                    if y1 > y2:
                        return 1
                    elif y1 < y2:
                        return -1
                # The "longer" version is greater
                d = cp_len(t2)
                if d:
                    return d
            else:
                if x1 > x2:
                    return 1
                elif x1 < x2:
                    return -1
            i += 1

        # The "shorter" version is greater
        return cp_len(t1, 1)
