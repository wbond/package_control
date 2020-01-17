# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from . import backend
from ._asymmetric import parse_certificate, parse_private, parse_public


_backend = backend()


if _backend == 'mac':
    from ._mac.asymmetric import parse_pkcs12
elif _backend == 'win' or _backend == 'winlegacy':
    from ._win.asymmetric import parse_pkcs12
else:
    from ._openssl.asymmetric import parse_pkcs12


__all__ = [
    'parse_certificate',
    'parse_pkcs12',
    'parse_private',
    'parse_public',
]
