# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from . import backend


_backend = backend()


if _backend == 'osx':
    from ._osx.tls import (
        TLSSession,
        TLSSocket,
    )

elif _backend == 'win' or _backend == 'winlegacy':
    from ._win.tls import (
        TLSSession,
        TLSSocket,
    )

else:
    from ._openssl.tls import (
        TLSSession,
        TLSSocket,
    )


__all__ = [
    'TLSSession',
    'TLSSocket',
]
