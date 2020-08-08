# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from ctypes import CDLL, c_uint32, c_char_p, c_size_t, c_int, c_uint

from .._ffi import FFIEngineError


__all__ = [
    'CommonCrypto',
]


common_crypto_path = '/usr/lib/system/libcommonCrypto.dylib'

CommonCrypto = CDLL(common_crypto_path, use_errno=True)

try:
    CommonCrypto.CCKeyDerivationPBKDF.argtypes = [
        c_uint32,
        c_char_p,
        c_size_t,
        c_char_p,
        c_size_t,
        c_uint32,
        c_uint,
        c_char_p,
        c_size_t
    ]
    CommonCrypto.CCKeyDerivationPBKDF.restype = c_int
except (AttributeError):
    raise FFIEngineError('Error initializing ctypes')
