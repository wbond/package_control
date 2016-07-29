# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import locale

from .._types import str_cls


_encoding = locale.getpreferredencoding()
_fallback_encodings = ['utf-8', 'cp1252']


def _try_decode(byte_string):
    """
    Tries decoding a byte string from the OS into a unicode string

    :param byte_string:
        A byte string

    :return:
        A unicode string
    """

    try:
        return str_cls(byte_string, _encoding)

    # If the "correct" encoding did not work, try some defaults, and then just
    # obliterate characters that we can't seen to decode properly
    except (UnicodeDecodeError):
        for encoding in _fallback_encodings:
            try:
                return str_cls(byte_string, encoding, errors='strict')
            except (UnicodeDecodeError):
                pass

    return str_cls(byte_string, errors='replace')
