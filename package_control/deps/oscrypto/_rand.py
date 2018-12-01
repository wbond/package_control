# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import os

from ._errors import pretty_message
from ._types import type_name, int_types


__all__ = [
    'rand_bytes',
]


def rand_bytes(length):
    """
    Returns a number of random bytes suitable for cryptographic purposes

    :param length:
        The desired number of bytes

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by OpenSSL

    :return:
        A byte string
    """

    if not isinstance(length, int_types):
        raise TypeError(pretty_message(
            '''
            length must be an integer, not %s
            ''',
            type_name(length)
        ))

    if length < 1:
        raise ValueError('length must be greater than 0')

    if length > 1024:
        raise ValueError('length must not be greater than 1024')

    return os.urandom(length)
