# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import sys

from ._errors import pretty_message
from ._types import type_name, byte_cls

if sys.platform == 'darwin':
    from ._osx.util import rand_bytes
elif sys.platform == 'win32':
    from ._win.util import rand_bytes
else:
    from ._openssl.util import rand_bytes


__all__ = [
    'constant_compare',
    'rand_bytes',
]


def constant_compare(a, b):
    """
    Compares two byte strings in constant time to see if they are equal

    :param a:
        The first byte string

    :param b:
        The second byte string

    :return:
        A boolean if the two byte strings are equal
    """

    if not isinstance(a, byte_cls):
        raise TypeError(pretty_message(
            '''
            a must be a byte string, not %s
            ''',
            type_name(a)
        ))

    if not isinstance(b, byte_cls):
        raise TypeError(pretty_message(
            '''
            b must be a byte string, not %s
            ''',
            type_name(b)
        ))

    if len(a) != len(b):
        return False

    if sys.version_info < (3,):
        a = [ord(char) for char in a]
        b = [ord(char) for char in b]

    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0
