# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import ctypes
from ctypes import windll, wintypes, POINTER, c_longlong, Structure

from .._ffi import FFIEngineError
from .._types import str_cls
from ..errors import LibraryNotFoundError


__all__ = [
    'get_error',
    'kernel32',
]


try:
    kernel32 = windll.kernel32
except (OSError) as e:
    if str_cls(e).find('The specified module could not be found') != -1:
        raise LibraryNotFoundError('kernel32.dll could not be found')
    raise

LARGE_INTEGER = c_longlong

try:
    kernel32.QueryPerformanceCounter.argtypes = [POINTER(LARGE_INTEGER)]
    kernel32.QueryPerformanceCounter.restype = wintypes.BOOL

    class FILETIME(Structure):
        _fields_ = [
            ("dwLowDateTime", wintypes.DWORD),
            ("dwHighDateTime", wintypes.DWORD),
        ]

    kernel32.GetSystemTimeAsFileTime.argtypes = [POINTER(FILETIME)]
    kernel32.GetSystemTimeAsFileTime.restype = None

except (AttributeError):
    raise FFIEngineError('Error initializing ctypes')


setattr(kernel32, 'LARGE_INTEGER', LARGE_INTEGER)
setattr(kernel32, 'FILETIME', FILETIME)


def get_error():
    error = ctypes.GetLastError()
    return (error, ctypes.FormatError(error))
