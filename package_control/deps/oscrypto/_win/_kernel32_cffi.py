# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from .._ffi import register_ffi
from .._types import str_cls
from ..errors import LibraryNotFoundError

import cffi


__all__ = [
    'get_error',
    'kernel32',
]


ffi = cffi.FFI()
if cffi.__version_info__ >= (0, 9):
    ffi.set_unicode(True)
ffi.cdef("""
    typedef long long LARGE_INTEGER;
    BOOL QueryPerformanceCounter(LARGE_INTEGER *lpPerformanceCount);

    typedef struct _FILETIME {
        DWORD dwLowDateTime;
        DWORD dwHighDateTime;
    } FILETIME;

    void GetSystemTimeAsFileTime(FILETIME *lpSystemTimeAsFileTime);
""")


try:
    kernel32 = ffi.dlopen('kernel32.dll')
    register_ffi(kernel32, ffi)

except (OSError) as e:
    if str_cls(e).find('cannot load library') != -1:
        raise LibraryNotFoundError('kernel32.dll could not be found')
    raise


def get_error():
    return ffi.getwinerror()
