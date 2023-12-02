import os
import platform
import re
import sys


TOKEN_REGEX = re.compile(
    r"(\bpython_version\b)|"
    r"(\bpython_full_version\b)|"
    r"(\bos\.name\b)|"
    r"(\bsys\.platform)|"
    r"(\bplatform\.version\b)|"
    r"(\bplatform\.machine\b)|"
    r"(\bplatform\.python_implementation\b)|"
    r"(\bimplementation_name\b)|"
    r"(\bimplementation_version\b)|"
    r"(\"[^\"]*\"|'[^']*')|"
    r"(\bor\b)|"
    r"(\band\b)|"
    r"(\bnot\s+in\b)|"
    r"(\bin\b)|"
    r"(===)|"
    r"(==)|"
    r"(!=)|"
    r"(~=)|"
    r"(<=)|"
    r"(<)|"
    r"(>=)|"
    r"(>)|"
    r"(,)"
)

NONE = 0

PYTHON_VERSION = 1
PYTHON_FULL_VERSION = 2
OS_NAME = 3
SYS_PLATFORM = 4
PLATFORM_VERSION = 5
PLATFORM_MACHINE = 6
PLATFORM_PYTHON_IMPLEMENTATION = 7
IMPLEMENTATION_NAME = 8
IMPLEMENTATION_VERSION = 9
STRING = 10
OP_OR = 11
OP_AND = 12
OP_NOT_IN = 13
OP_IN = 14
OP_STRICT_EQ = 15
OP_EQ = 16
OP_NE = 17
OP_COMPAT_EQ = 18
OP_LTE = 19
OP_LT = 20
OP_GTE = 21
OP_GT = 22
OP_COMMA = 23

LOGICAL_OPERATORS = {
    OP_AND,
    OP_OR,
    OP_COMMA,
}
LOGICAL_OPERATOR = 1

COMPARISON_OPERATORS = {
    OP_NOT_IN,
    OP_IN,
    OP_EQ,
    OP_NE,
    OP_STRICT_EQ,
    OP_COMPAT_EQ,
    OP_LT,
    OP_LTE,
    OP_GT,
    OP_GTE,
}
COMPARISON_OPERATOR = 2

VALUE = 3


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


MARKERS = {
    PYTHON_VERSION: '.'.join(platform.python_version_tuple()[:2]),
    PYTHON_FULL_VERSION: platform.python_version(),
    OS_NAME: os.name,
    SYS_PLATFORM: sys.platform,
    PLATFORM_VERSION: platform.version(),
    PLATFORM_MACHINE: platform.machine(),
    PLATFORM_PYTHON_IMPLEMENTATION: platform.python_implementation(),
    IMPLEMENTATION_NAME: _implementation_name(),
    IMPLEMENTATION_VERSION: _implementation_version(),
}


def _token_name(token_type):
    return {
        NONE: "NONE",
        PYTHON_VERSION: "PYTHON VERSION",
        PYTHON_FULL_VERSION: "PYTHON FULL VERSION",
        OS_NAME: "OS NAME",
        SYS_PLATFORM: "SYS PLATFORM",
        PLATFORM_VERSION: "PLATFORM VERSION",
        PLATFORM_MACHINE: "PLATFORM MACHINE",
        PLATFORM_PYTHON_IMPLEMENTATION: "PLATFORM PYTHON IMPLEMENTATION",
        IMPLEMENTATION_NAME: "IMPLEMENTATION NAME",
        IMPLEMENTATION_VERSION: "IMPLEMENTATION VERSION",
        STRING: "STRING",
        OP_OR: "OR",
        OP_AND: "AND",
        OP_NOT_IN: "NOT IN",
        OP_IN: "IN",
        OP_EQ: "EQUAL",
        OP_NE: "NOT EQUAL",
        OP_STRICT_EQ: "STRICT EQUAL",
        OP_COMPAT_EQ: "COMPATIBLE EQUAL",
        OP_LT: "LESS THAN",
        OP_LTE: "LESS THAN EQUAL",
        OP_GT: "GREATER THAN",
        OP_GTE: "GREATER THAN EQUAL",
        OP_COMMA: "COMMA",
    }[token_type]


def _category_name(category):
    return {
        NONE: "NONE",
        LOGICAL_OPERATOR: "LOGICAL OPERATOR",
        COMPARISON_OPERATOR: "COMPARISON OPERATOR",
        VALUE: "VALUE",
    }[category]


class Token():
    token_type = 0
    # Only used for strings
    value = None
    span = None

    def __init__(self, token_type, value, span):
        self.token_type = token_type
        self.value = value
        self.span = span

    def category(self):
        if self.token_type in LOGICAL_OPERATORS:
            return LOGICAL_OPERATOR
        if self.token_type in COMPARISON_OPERATORS:
            return COMPARISON_OPERATOR
        if self.token_type == NONE:
            return NONE
        return VALUE

    def realize(self):
        if self.token_type == STRING:
            return self.value

        if self.token_type not in MARKERS:
            raise RuntimeError("Unable to realize token of type %s" % _token_name(self.token_type))

        return MARKERS[self.token_type]


class Parser():
    remaining = None

    def __init__(self, text):
        self.remaining = text

    def empty(self):
        if self.remaining is None:
            return True
        return not len(self.remaining)

    def next(self):
        if self.remaining is None:
            raise ValueError("no remaining text to parse")

        match = TOKEN_REGEX.search(self.remaining)
        if match is None:
            self.remaining = None
            return Token(NONE, None, (-1, -1))

        token_type = match.lastindex
        value = None
        if token_type == STRING:
            value = match.group(token_type)[1:-1]

        self.remaining = self.remaining[match.end():]
        return Token(token_type, value, match.span())


class PEP508EnvironmentMarker():
    tokens = None

    def __init__(self, string):
        parser = Parser(string)

        tokens = []
        while not parser.empty():
            token = parser.next()
            if token.token_type == OP_COMMA:
                raise ValueError(
                    "Unexpected token %s of type %s at %d" % (
                        _token_name(token.token_type),
                        _category_name(token.category),
                        token.span[0]
                    )
                )
            if token.token_type != 0:
                tokens.append(token)

        num_values = 0
        expected = VALUE
        for token in tokens:
            category = token.category()

            if category != expected:
                raise ValueError(
                    "Unexpected token %s of type %s at %d, expecting %s" % (
                        _token_name(token.token_type),
                        _category_name(category),
                        token.span[0],
                        _category_name(expected)
                    )
                )

            if expected == VALUE:
                num_values += 1
                if num_values % 2 == 0:
                    expected = LOGICAL_OPERATOR
                else:
                    expected = COMPARISON_OPERATOR
            elif expected == COMPARISON_OPERATOR:
                expected = VALUE
            elif expected == LOGICAL_OPERATOR:
                expected = VALUE

        if expected != LOGICAL_OPERATOR:
            raise ValueError(
                "Incomplete expression, expecting %s at %d" % (
                    _category_name(expected),
                    len(string)
                )
            )

        self.tokens = tokens

    def check(self):
        result = True

        old_value = None
        value = None
        comparison_operator = None
        logical_operator = None

        num_values = 0

        for token in self.tokens:
            category = token.category()

            if category == VALUE:
                num_values += 1
                old_value = value
                value = token.realize()

                if num_values % 2 == 0:
                    if comparison_operator == OP_NOT_IN:
                        sub_result = old_value not in value
                    elif comparison_operator == OP_IN:
                        sub_result = old_value in value
                    elif comparison_operator == OP_EQ:
                        sub_result = old_value == value
                    elif comparison_operator == OP_NE:
                        sub_result = old_value != value

                    if logical_operator is None:
                        result = sub_result
                    elif logical_operator == OP_OR:
                        result = result or sub_result
                    elif logical_operator == OP_AND:
                        result = result and sub_result

            elif category == COMPARISON_OPERATOR:
                comparison_operator = token.token_type

            elif category == LOGICAL_OPERATOR:
                logical_operator = token.token_type

        return result
