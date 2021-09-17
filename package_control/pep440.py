import re


def _pep440_to_tuple(version_string):
    """
    Constructs a tuple of integers that allows comparing valid PEP440 versions

    :param version_string:
        A unicode PEP440 version string

    :return:
        A tuple of integers
    """

    match = re.search(
        r'(?:(\d+)\!)?'
        r'(\d+(?:\.\d+)*)'
        r'([-._]?(?:alpha|a|beta|b|preview|pre|c|rc)\.?\d*)?'
        r'(-\d+|(?:[-._]?(?:rev|r|post)\.?\d*))?'
        r'([-._]?dev\.?\d*)?',
        version_string
    )
    if not match:
        return tuple()

    epoch = match.group(1)
    if epoch:
        epoch = int(epoch)
    else:
        epoch = 0

    nums = tuple(map(int, match.group(2).split('.')))

    pre = match.group(3)
    if pre:
        pre = pre.replace('alpha', 'a')
        pre = pre.replace('beta', 'b')
        pre = pre.replace('preview', 'rc')
        pre = pre.replace('pre', 'rc')
        pre = re.sub(r'(?<!r)c', 'rc', pre)
        pre = pre.lstrip('._-')
        pre_dig_match = re.search(r'\d+', pre)
        if pre_dig_match:
            pre_dig = int(pre_dig_match.group(0))
        else:
            pre_dig = 0
        pre = pre.rstrip('0123456789')

        pre_num = {
            'a': -3,
            'b': -2,
            'rc': -1,
        }[pre]

        pre_tup = (pre_num, pre_dig)
    else:
        pre_tup = tuple()

    post = match.group(4)
    if post:
        post_dig_match = re.search(r'\d+', post)
        if post_dig_match:
            post_dig = int(post_dig_match.group(0))
        else:
            post_dig = 0
        post_tup = (1, post_dig)
    else:
        post_tup = tuple()

    dev = match.group(5)
    if dev:
        dev_dig_match = re.search(r'\d+', dev)
        if dev_dig_match:
            dev_dig = int(dev_dig_match.group(0))
        else:
            dev_dig = 0
        dev_tup = (-4, dev_dig)
    else:
        dev_tup = tuple()

    normalized = [epoch, nums]
    if pre_tup:
        normalized.append(pre_tup)
    if post_tup:
        normalized.append(post_tup)
    if dev_tup:
        normalized.append(dev_tup)
    # This ensures regular releases happen after dev and prerelease, but
    # before post releases
    if not pre_tup and not post_tup and not dev_tup:
        normalized.append((0, 0))

    return tuple(normalized)


def _norm_tuples(a, b):
    """
    Accepts two tuples of PEP440 version numbers and extends them until they
    are the same length. This allows for comparisons between them.

    :param a:
        A tuple from _pep440_to_tuple()

    :param b:
        A tuple from _pep440_to_tuple()

    :return:
        Two potentially modified tuples, (a, b)
    """

    while len(a) < len(b):
        a = a + ((0,),)
    while len(a) > len(b):
        b = b + ((0,),)

    for i in range(1, len(a)):
        while len(a[i]) < len(b[i]):
            a = a[:i] + (a[i] + (0,),) + a[i + 1:]
        while len(a[i]) > len(b[i]):
            b = b[:i] + (b[i] + (0,),) + b[i + 1:]

    return a, b


class PEP440Version():
    string = ''
    tup = tuple()
    # Versions allow wildcards when used with == operator
    wildcard = False

    def __init__(self, string):
        self.wildcard = False
        if string.endswith(".*"):
            string = string[:-2]
            self.wildcard = True
        self.string = string
        self.tup = _pep440_to_tuple(string)

    def __str__(self):
        return self.string

    def __repr__(self):
        return 'PEP440Version(' + repr(self.string) + ')'

    def __eq__(self, rhs):
        a, b = _norm_tuples(self.tup, rhs.tup)
        return a == b

    def __ne__(self, rhs):
        a, b = _norm_tuples(self.tup, rhs.tup)
        return a != b

    def __lt__(self, rhs):
        a, b = _norm_tuples(self.tup, rhs.tup)
        return a < b

    def __le__(self, rhs):
        a, b = _norm_tuples(self.tup, rhs.tup)
        return a <= b

    def __gt__(self, rhs):
        a, b = _norm_tuples(self.tup, rhs.tup)
        return a > b

    def __ge__(self, rhs):
        a, b = _norm_tuples(self.tup, rhs.tup)
        return a >= b

    def __hash__(self):
        return hash(self.string)


def pep440_version_specifier(string):
    match = re.match(r'^(<=?|>=?|===|==|!=|~=)?\s*(\d.*)$', string.strip())
    if not match:
        raise ValueError("Unable to parse PEP 440 version specifier: %r" % string)

    operator = match.group(1) or "=="
    pep440_version = PEP440Version(match.group(2))

    return PEP440VersionComparator(operator, pep440_version)


class PEP440VersionComparator():
    operator = None
    pep440_version = None

    def __init__(self, operator, pep440_version):
        self.operator = operator
        self.pep440_version = pep440_version

    def check(self, version):
        """
        Ensures the version matches this specifier

        :param version:
            A PEP440Version() object to check

        :return:
            A bool if the version matches this specifier
        """

        ver_tup = version.tup

        eq = self.operator == "=="
        ne = self.operator == "!="

        if (eq or ne) and self.pep440_version.wildcard:
            lower_bound = self.pep440_version.tup
            upper_bound = (lower_bound[0], lower_bound[1][:-1] + (lower_bound[1][-1] + 1,), lower_bound[2])
            lower_bound, ver_tup = _norm_tuples(lower_bound, ver_tup)
            ver_tup, upper_bound = _norm_tuples(ver_tup, upper_bound)
            if eq:
                return ver_tup >= lower_bound and ver_tup < upper_bound
            if ne:
                return ver_tup < lower_bound or ver_tup >= upper_bound

        self_tup = self.pep440_version.tup
        self_tup, ver_tup = _norm_tuples(self_tup, ver_tup)

        if eq:
            return ver_tup == self_tup

        if ne:
            return ver_tup != self_tup

        if self.operator == ">=":
            return ver_tup >= self_tup

        if self.operator == ">":
            return ver_tup > self_tup

        if self.operator == "<=":
            return ver_tup <= self_tup

        if self.operator == "<":
            return ver_tup < self_tup

        raise ValueError("Invalid PEP 440 version specifier operator: %r" % self.operator)
