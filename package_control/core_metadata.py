import os
import platform
import re
import sys


class ClassInst(type):
    """
    A metaclass that allows using classes as value classes that
    display as the class name when calling repr() on it
    """

    def __init__(cls, name, bases, dict):
        name = cls.__name__
        if name[-1:].isupper():
            name = name[:-1]
        cls.name = re.sub(
            r'([a-z])([A-Z])',
            '\1 \2',
            name
        ).upper()

    def __repr__(cls):
        return str(cls.__name__)


class TokenCategory(metaclass=ClassInst):
    """
    A base value class for the category that a Token may be
    a part of.

    The value is an integer that is the bitwise OR of one or
    more categories.

    If a Token.category value is bitwise AND with a
    TokenCategory.value and the result is non-zero, the Token is
    part of the TokenCategory.
    """

    value = 0


class LogicalOperatorC(TokenCategory):
    value = 1


class ComparisonOperatorC(TokenCategory):
    value = 2


class GroupingOperatorC(TokenCategory):
    value = 4


class OperatorC(TokenCategory):
    value = 7


class LiteralC(TokenCategory):
    value = 8


class IdentifierC(TokenCategory):
    value = 16


class ValueC(TokenCategory):
    value = 24


class UncategorizedC(TokenCategory):
    value = 32


class TokenType(metaclass=ClassInst):
    """
    A base value class that is used to track what type of token a Token
    object is. The regex is used to construct the mater regex used by
    Lexer to lex text. The category is used when writing logic in the
    Parser.
    """

    regex = r""
    category = TokenCategory


class ValueTokenType(TokenType):
    """
    A base value class for all token types that represent a value, such
    as a string literal or identifier. Value token types can
    be resolved to a value at run time.
    """

    pass


class PythonVersionT(ValueTokenType):
    regex = r"\bpython_version\b"
    category = IdentifierC


class PythonFullVersionT(ValueTokenType):
    regex = r"\bpython_full_version\b"
    category = IdentifierC


class OsNameT(ValueTokenType):
    regex = r"\bos\.name\b"
    category = IdentifierC


class SysPlatformT(ValueTokenType):
    regex = r"\bsys\.platform\b"
    category = IdentifierC


class PlatformVersionT(ValueTokenType):
    regex = r"\bplatform\.version\b"
    category = IdentifierC


class PlatformMachineT(ValueTokenType):
    regex = r"\bplatform\.machine\b"
    category = IdentifierC


class PlatformPythonImplementationT(ValueTokenType):
    regex = r"\bplatform\.python_implementation\b"
    category = IdentifierC


class ImplementationNameT(ValueTokenType):
    regex = r"\bimplementation_name\b"
    category = IdentifierC


class ImplementationVersionT(ValueTokenType):
    regex = r"\bimplementation_version\b"
    category = IdentifierC


class StringT(ValueTokenType):
    regex = r"\"[^\"]*\"|'[^']*'"
    category = LiteralC


class OrT(TokenType):
    regex = r"\bor\b"
    category = LogicalOperatorC


class AndT(TokenType):
    regex = r"\band\b"
    category = LogicalOperatorC


class NotInT(TokenType):
    regex = r"\bnot\s+in\b"
    category = ComparisonOperatorC


class InT(TokenType):
    regex = r"\bin\b"
    category = ComparisonOperatorC


class StrictEqualT(TokenType):
    regex = r"==="
    category = ComparisonOperatorC


class EqualT(TokenType):
    regex = r"=="
    category = ComparisonOperatorC


class NotEqualT(TokenType):
    regex = r"!="
    category = ComparisonOperatorC


class CompatEqualT(TokenType):
    regex = r"~="
    category = ComparisonOperatorC


class LessThanEqualT(TokenType):
    regex = r"<="
    category = ComparisonOperatorC


class LessThanT(TokenType):
    regex = r"<"
    category = ComparisonOperatorC


class GreaterThanEqualT(TokenType):
    regex = r">="
    category = ComparisonOperatorC


class GreaterThanT(TokenType):
    regex = r">"
    category = ComparisonOperatorC


class CommaT(TokenType):
    regex = r","
    category = LogicalOperatorC


class SemicolonT(TokenType):
    regex = r";"
    category = GroupingOperatorC


class OpenParenT(TokenType):
    regex = r"\("
    category = GroupingOperatorC


class CloseParenT(TokenType):
    regex = r"\)"
    category = GroupingOperatorC


class OpenBracketT(TokenType):
    regex = r"\["
    category = GroupingOperatorC


class CloseBracketT(TokenType):
    regex = r"\]"
    category = GroupingOperatorC


class IdentifierT(ValueTokenType):
    regex = r"\b(?:[A-Za-z]|[A-Za-z][A-Za-z0-9._\-]*[A-Za-z0-9_])\b"
    category = IdentifierC


class StarVersionT(ValueTokenType):
    # Versions with .* at the end can't be pre or post releases
    regex = r"(?:[1-9][0-9]*!)?(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*))*\.\*(?![\-.0-9a-zA-Z])"
    category = LiteralC


class VersionT(ValueTokenType):
    regex = r"(?:[1-9][0-9]*!)?" + \
        r"(?:0|[1-9][0-9]*)" + \
        r"(?:\.(?:0|[1-9][0-9]*))*" + \
        r"(?:(?:a|b|rc)(?:0|[1-9][0-9]*))?" + \
        r"(?:\.post(?:0|[1-9][0-9]*))?" + \
        r"(?:\.dev(?:0|[1-9][0-9]*))?" + \
        r"(?![\-.0-9a-zA-Z])"
    category = LiteralC


class UnexpectedT(TokenType):
    regex = r"\S+"
    category = UncategorizedC


class EndOfFileT(TokenType):
    regex = r"$"
    category = UncategorizedC


class Action(metaclass=ClassInst):
    """
    The base value class for actions to be performed by Transition objects
    that are used by the Parser
    """

    pass


class Replace(Action):
    pass


class Push(Action):
    pass


class Pop(Action):
    pass


class State(metaclass=ClassInst):
    """
    The base value class for states that are used by the Parser
    """

    pass


# A list of all supported tokens, in lexing priority order. Is used
# to construct the TOKEN_REGEX that is used by the Lexer.
TOKEN_TYPES = [
    PythonVersionT,
    PythonFullVersionT,
    OsNameT,
    SysPlatformT,
    PlatformVersionT,
    PlatformMachineT,
    PlatformPythonImplementationT,
    ImplementationNameT,
    ImplementationVersionT,
    StringT,
    OrT,
    AndT,
    NotInT,
    InT,
    StrictEqualT,
    EqualT,
    NotEqualT,
    CompatEqualT,
    LessThanEqualT,
    LessThanT,
    GreaterThanEqualT,
    GreaterThanT,
    CommaT,
    SemicolonT,
    OpenParenT,
    CloseParenT,
    OpenBracketT,
    CloseBracketT,
    IdentifierT,
    StarVersionT,
    VersionT,
    UnexpectedT,
    EndOfFileT,
]
TOKEN_REGEX = re.compile(
    r"(" +
    r")|(".join([tt.regex for tt in TOKEN_TYPES]) +
    r")"
)


class Token:
    """
    Represents a token from text, as found by Lexer. Used by the Parser
    to parse various metadata about packages.
    """

    token_type = TokenType
    span = None
    value = None

    def __init__(self, token_type, span, value=None):
        self.token_type = token_type
        self.span = span
        self.value = value

    def __repr__(self):
        if self.token_type.category is LiteralC:
            return 'Token(%s, %r, %r)' % (self.token_type.__name__, self.span, self.value)
        return 'Token(%s, %r)' % (self.token_type.__name__, self.span)

    @property
    def description(self):
        if self.value is None:
            return self.token_type.name
        if self.token_type is StringT:
            return self.token_type.name + ' (' + repr(self.value) + ')'
        return self.token_type.name + ' (' + self.value + ')'

    @property
    def category(self):
        return self.token_type.category


class Lexer:
    """
    A lexer that creates Token objects from a unicode string, used by
    the Parser class
    """

    text = None
    length = 0
    position = 0

    def __init__(self, text):
        """
        :param text:
            The unicode string to lex
        """

        self.text = text
        self.length = len(text)
        self.position = 0

    def empty(self):
        """
        :return:
            A bool if there is any text remaining to lex
        """

        if self.text is None:
            return True
        return bool(self.length - self.position)

    def rewind(self, token):
        """
        :param token:
            A Token to push back into the lexer
        """

        self.position = token.span[0]

    def next(self):
        """
        :raises:
            A ValueError if there is no text remaining to lex

        :return:
            The next Token object in the text
        """

        if self.text is None:
            raise ValueError("no text to parse")

        if self.length - self.position == -1:
            raise ValueError("no remaining text to parse")

        if self.length - self.position == 0:
            self.position = self.length + 1
            return Token(EndOfFileT, (self.position - 1, self.position - 1))

        match = TOKEN_REGEX.search(self.text, self.position)
        if match is None:
            self.position = self.length + 1
            return Token(EndOfFileT, (self.position - 1, self.position - 1))

        token_type_idx = match.lastindex - 1
        token_type = TOKEN_TYPES[token_type_idx]

        span = (match.start(), match.end())

        value = None
        if token_type == StringT:
            value = match.group(match.lastindex)[1:-1]
        elif token_type.category in set([LiteralC, LogicalOperatorC, ComparisonOperatorC, IdentifierC]):
            value = match.group(match.lastindex)

        self.position = match.end()

        return Token(token_type, span, value)


class Transition:
    """
    A transition rule for the Parse class
    """

    match = None
    action = Action
    state = 0
    is_category = True

    def __init__(self, match, action, state=None):
        """
        :param match:
            A subclass of Token or TokenCategory

        :param action:
            A subclass of Action denoting what to do when a match is made

        :param state:
            When the action is not Pop, the State subclass that should be added or
            replaced on the stack
        """

        self.match = match
        self.action = action
        if action != Pop and state is None:
            raise ValueError("A state is required when the action is not Pop")
        self.state = state
        self.is_category = issubclass(match, TokenCategory)

    def __repr__(self):
        if self.state is not None:
            return 'Transition(%s, %s, %r)' % (self.match, self.action, self.state)
        return 'Transition(%s, %s)' % (self.match, self.action)

    def matches(self, token):
        if self.is_category:
            return bool(token.token_type.category.value & self.match.value)
        return issubclass(token.token_type, self.match)


class Parser:
    """
    Parses a string into a series of Token objects based on state rules
    """

    rules = None
    stack = None
    tokens = None
    lexer = None

    def __init__(self, rules, initial_state, text, on_unmatched=None):
        """
        :param rules:
            A dict where keys are State subclasses and values are a list of Transition
            objects

        :param initial_state:
            The State subclass to start the parser in

        :param text:
            The unicode text to parse
        """

        self.rules = rules
        self.stack = [initial_state]
        self.tokens = []
        self.lexer = Lexer(text)
        self.on_unmatched = on_unmatched or self._default_on_unmatched

    def _default_on_unmatched(self, token, stack):
        raise ValueError(
            "Unexpected token %s at %d, state %s" % (
                token.description,
                token.span[0],
                stack[-1].name
            )
        )

    def parse(self):
        token = self.lexer.next()
        while token and token.token_type != EndOfFileT:
            matched = False
            for trans in self.rules[self.stack[-1]]:
                if trans.matches(token):
                    matched = True
                    self.tokens.append(token)
                    action = trans.action
                    if action == Push:
                        self.stack.append(trans.state)
                    elif action == Pop:
                        if len(self.stack) == 1:
                            matched = False
                            break
                        self.stack.pop()
                        if trans.state:
                            self.stack[-1] = trans.state
                    elif action == Replace:
                        self.stack[-1] = trans.state
                    break

            if not matched:
                self.on_unmatched(token, self.stack)
                return

            token = self.lexer.next()

        if len(self.stack) != 1:
            raise ValueError(
                "Unexpected end of expression at %d" % token.span[0]
            )


##########
# PEP 440
##########


def _pep440_to_tuple(version_string):
    """
    Constructs a tuple of integers that allows comparing valid PEP440 versions

    :param version_string:
        A unicode PEP440 version string

    :return:
        A 3+ element tuple:
        0: integer epoch number
        1: a tuple of 1 or more integers
        2: a tuple of two integers
           the first integer is the type of segment:
            -4 = dev
            -3 = alpha
            -2 = beta
            -1 = rc
            0 = regular release
            1 = post
           the second integer is the number for the release,
           e.g. 1 for post1 or 4 for a4. If a release has no
           number, then the second integer is 0.
        3: if index 2 is alpha, beta, rc or post then this
           index may be present, and will be a 2-integer
           tuple for a dev release
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


def _mod_version_tuple(tup, release=False, suffix=False):
    """
    Allows modifying a version tuple from _pep440_to_tuple()

    :param tup:
        The original version tuple

    :param release:
        This parameter allows the release tuple (tup[1]) to be modified.
         - If False, the release tuple is not modified
         - If None, the release tuple has the last integer removed
         - If an integer, the last integer in the release tuple is modified by the integer

    :param suffix:
        This parameter allows the suffix tuples (tup[2:]) to be modified.
         - If False, the suffix tuples are not modified
         - If None, the suffix tuples are reset to ((0, 0),)

    :return:
        The modified version tuple
    """

    if release is False and suffix is False:
        raise ValueError('Either release or suffix param must have a value other than False')

    if release is None:
        tup = (tup[0], tup[1][:-1]) + tup[2:]
    elif isinstance(release, int):
        tup = (tup[0], tup[1][:-1] + (tup[1][-1] + release,)) + tup[2:]
    elif release is not False:
        raise TypeError('release must False, None or an integer')

    if suffix is None:
        tup = (tup[0], tup[1], (0, 0))
    elif suffix is not False:
        raise TypeError('suffix must False or None')

    return tup


def _normalize_wildcard_tuples(version_tup, wildcard_tup):
    """
    Normalizes a version and a wildcard version creating lower
    and upper bounds for comparison

    :param version_tup:
        A tuple from _pep440_to_tuple() that represents the version to check

    :param wildcard_tup:
        A tuple from _pep440_to_tuple() of the wildcard version, minus the
        wildcard. For example, for 1.2.*, this should be _pep440_to_tuple('1.2')

    :return:
        A 3-element tuple:
         0: The inclusive lower bound pep440-tuple from wildcard_tup
         1: The exclusive upper bound pep440-tuple from wildcard_tup
         2: The length-normalized version_tup
    """

    # Wildcard matches always work for pre and post releases, so we
    # remove that from the version we are comparing
    version_tup = _mod_version_tuple(version_tup, suffix=None)

    # Since we ignore the pre and post release, we set index 2
    # of the lower and upper bounds to a plain (0, 0)
    lower_bound = _mod_version_tuple(wildcard_tup, suffix=None)
    upper_bound = _mod_version_tuple(lower_bound, release=1)
    lower_bound, version_tup = _norm_tuples(lower_bound, version_tup)
    version_tup, upper_bound = _norm_tuples(version_tup, upper_bound)
    return (lower_bound, upper_bound, version_tup)


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


class OperatorS(State):
    pass


class VersionS(State):
    pass


class StrictVersionS(State):
    pass


class MaybeCommaS(State):
    pass


class PEP440VersionSpecifier:
    tokens = None

    RULES = {
        OperatorS: [
            Transition(CompatEqualT, Replace, VersionS),
            Transition(StrictEqualT, Replace, StrictVersionS),
            Transition(EqualT, Replace, VersionS),
            Transition(NotEqualT, Replace, VersionS),
            Transition(LessThanEqualT, Replace, VersionS),
            Transition(GreaterThanEqualT, Replace, VersionS),
            Transition(LessThanT, Replace, VersionS),
            Transition(GreaterThanT, Replace, VersionS),
            Transition(StarVersionT, Replace, MaybeCommaS),
            Transition(VersionT, Replace, MaybeCommaS),
        ],
        VersionS: [
            Transition(StarVersionT, Replace, MaybeCommaS),
            Transition(VersionT, Replace, MaybeCommaS),
        ],
        StrictVersionS: [
            Transition(StarVersionT, Replace, MaybeCommaS),
            Transition(VersionT, Replace, MaybeCommaS),
            Transition(IdentifierT, Replace, MaybeCommaS),
        ],
        MaybeCommaS: {
            Transition(CommaT, Replace, OperatorS),
            Transition(EndOfFileT, Pop),
        },
    }

    def __init__(self, string):
        parser = Parser(self.RULES, OperatorS, string)
        parser.parse()
        self.tokens = parser.tokens

    def __repr__(self):
        return repr(self.tokens)

    def check(self, version):

        if not isinstance(version, PEP440Version):
            raise TypeError('version must be an instance of PEP440Version')
        version_tup = version.tup

        operator = None

        for token in self.tokens:
            category = token.category

            if token.token_type == CommaT:
                operator = None

            elif category.value & ComparisonOperatorC.value:
                operator = token.token_type

            else:
                if operator is None:
                    operator = EqualT

                token_string = token.value

                # The strict equal does only literal string matching per PEP440
                if operator == StrictEqualT:
                    if token_string != version.string:
                        return False
                    continue

                token_ver = PEP440Version(token_string)
                raw_tup = token_ver.tup
                token_tup = raw_tup

                lower_bound = None
                upper_bound = None
                wildcard_ver_tup = None

                trailing_version = token_tup[2][0]
                is_pre_release = trailing_version < 0
                is_post_release = trailing_version > 0

                if token_ver.wildcard:
                    if operator != EqualT and operator != NotEqualT:
                        raise ValueError(
                            'Wildcard versions are only supported by the == and != operators, not %s' % token.value
                        )
                    lower_bound, upper_bound, wildcard_ver_tup = _normalize_wildcard_tuples(version_tup, token_tup)
                else:
                    token_tup, version_tup = _norm_tuples(token_tup, version_tup)

                if operator == EqualT:
                    if token_ver.wildcard:
                        if wildcard_ver_tup < lower_bound or wildcard_ver_tup >= upper_bound:
                            return False
                    else:
                        if version_tup != token_tup:
                            return False

                elif operator == NotEqualT:
                    if token_ver.wildcard:
                        if wildcard_ver_tup >= lower_bound and wildcard_ver_tup < upper_bound:
                            return False
                    else:
                        if version_tup == token_tup:
                            return False

                elif operator == CompatEqualT:
                    if len(token_ver.tup[1]) < 2:
                        raise ValueError(
                            'The compatible release selector ~= can not be used with a single segment'
                            ' version number, but %r was provided' % token_string
                        )
                    if version_tup < token_tup:
                        return False
                    # The algorithm requires removing any pre, post or dev release info,
                    # plus the final number from the main version tuple
                    trimmed_token_tup = _mod_version_tuple(raw_tup, release=None, suffix=None)
                    lower_bound, upper_bound, wildcard_ver_tup = _normalize_wildcard_tuples(
                        version_tup,
                        trimmed_token_tup
                    )
                    if wildcard_ver_tup < lower_bound or wildcard_ver_tup >= upper_bound:
                        return False

                elif operator == GreaterThanEqualT:
                    if version_tup < token_tup:
                        return False

                elif operator == GreaterThanT:
                    # PEP 440 requires that >V must not match any post release, unless
                    # the version specified is a post release
                    if not is_post_release:
                        incr_tup = _mod_version_tuple(token_tup, release=1, suffix=None)
                        incr_tup, version_tup = _norm_tuples(incr_tup, version_tup)
                        if version_tup < incr_tup:
                            return False
                    else:
                        if version_tup <= token_tup:
                            return False

                elif operator == LessThanEqualT:
                    if version_tup > token_tup:
                        return False

                elif operator == LessThanT:
                    # PEP 440 requires that <V must not match any pre release, unless
                    # the version specified is a pre release
                    if not is_pre_release:
                        decr_tup = _mod_version_tuple(token_tup, release=-1, suffix=None)
                        decr_tup, version_tup = _norm_tuples(decr_tup, version_tup)
                        if version_tup > decr_tup:
                            return False
                    else:
                        if version_tup >= token_tup:
                            return False

        return True


##########
# PEP 508
##########


class ValueS(State):
    pass


class SecondValueS(State):
    pass


class LogicalOperatorS(State):
    pass


def _in_map(token, value_map):
    return value_map is not None and token.value in value_map


def _is_mapped_value(token, single_value_map, multi_value_map):
    if token is None:
        return False
    if token.token_type != IdentifierT:
        return False
    if _in_map(token, single_value_map):
        return True
    if _in_map(token, multi_value_map):
        return True
    return False


def _map_value_operator(token, operator, single_value_map, multi_value_map):
    if not _is_mapped_value(token, single_value_map, multi_value_map):
        return None, None

    if _in_map(token, single_value_map):
        value = single_value_map[token.value]
        return value, None

    if _in_map(token, multi_value_map):
        value = multi_value_map[token.value]
        new_operator = None
        if operator == EqualT:
            new_operator = InT
        elif operator == NotEqualT:
            new_operator = NotInT
        return value, new_operator

    return None, None


def _non_string_iterable(value):
    return hasattr(type(value), '__iter__') and not isinstance(value, str)


def _implementation_name():
    if hasattr(sys, 'implementation'):
        return sys.implementation.name
    return ''


def _implementation_version():
    if hasattr(sys, 'implementation'):
        vi = sys.implementation.version
        version = '{0.major}.{0.minor}.{0.micro}'.format(vi)
        kind = vi.releaselevel
        if kind != 'final':
            version += kind[0] + str(vi.serial)
        return version
    return '0'


# The PEP 508 markers for the current machine
PEP508_MARKERS = {
    PythonVersionT: '.'.join(platform.python_version_tuple()[:2]),
    PythonFullVersionT: platform.python_version(),
    OsNameT: os.name,
    SysPlatformT: sys.platform,
    PlatformVersionT: platform.version(),
    PlatformMachineT: platform.machine(),
    PlatformPythonImplementationT: platform.python_implementation(),
    ImplementationNameT: _implementation_name(),
    ImplementationVersionT: _implementation_version(),
}


def _realize(token):
    if not issubclass(token.token_type, ValueTokenType):
        raise RuntimeError("Unable to realize token of type %s" % token.token_type.name)

    if token.token_type in PEP508_MARKERS:
        return PEP508_MARKERS[token.token_type]

    return token.value


class PEP508EnvironmentMarker:
    tokens = None

    RULES = {
        ValueS: [
            Transition(OpenParenT, Push, ValueS),
            Transition(ValueC, Replace, OperatorS),
        ],
        OperatorS: {
            Transition(ComparisonOperatorC, Replace, SecondValueS),
        },
        SecondValueS: {
            Transition(ValueC, Replace, LogicalOperatorS)
        },
        LogicalOperatorS: {
            Transition(CloseParenT, Pop, LogicalOperatorS),
            Transition(LogicalOperatorC, Replace, ValueS),
            Transition(EndOfFileT, Pop)
        },
    }

    def __init__(self, string):
        parser = Parser(self.RULES, ValueS, string)
        parser.parse()
        self.tokens = parser.tokens

    def check(self, single_value_map=None, multi_value_map=None):
        result = True

        old_value = None
        value = None
        comparison_operator = None
        logical_operator = None

        num_values = 0

        for token in self.tokens:
            category = token.category

            value_is_mapped = _is_mapped_value(token, single_value_map, multi_value_map)

            # The token is an identifier that has multiple values, but we don't have an operator yet
            # we need to store the token and resolve it once we have an operator
            if value_is_mapped and num_values % 2 == 0:
                num_values += 1
                value = token

            elif issubclass(token.token_type, ValueTokenType):
                num_values += 1
                old_value = value

                new_operator = None
                if isinstance(old_value, Token) and _is_mapped_value(old_value, single_value_map, multi_value_map):
                    old_value, new_operator = _map_value_operator(
                        old_value,
                        comparison_operator,
                        single_value_map,
                        multi_value_map
                    )

                if value_is_mapped:
                    value, mapped_operator = _map_value_operator(
                        token,
                        comparison_operator,
                        single_value_map,
                        multi_value_map
                    )
                    new_operator = new_operator or mapped_operator
                else:
                    value = _realize(token)

                # If we swapped operators due to a multi-value mapping, we need to ensure
                # that the value order is valid with the operator
                if new_operator:
                    if _non_string_iterable(old_value) and not _non_string_iterable(value):
                        old_value, value = value, old_value
                    comparison_operator = new_operator

                if num_values % 2 == 0:
                    if comparison_operator == NotInT:
                        sub_result = old_value not in value
                    elif comparison_operator == InT:
                        sub_result = old_value in value
                    elif comparison_operator == EqualT:
                        sub_result = old_value == value
                    elif comparison_operator == NotEqualT:
                        sub_result = old_value != value

                    if logical_operator is None:
                        result = sub_result
                    elif logical_operator == OrT:
                        result = result or sub_result
                    elif logical_operator == AndT:
                        result = result and sub_result

            elif category.value & ComparisonOperatorC.value:
                comparison_operator = token.token_type

            elif category.value & LogicalOperatorC.value:
                logical_operator = token.token_type

        return result


def pep503_normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()
