# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from .._ffi import FFIEngineError

try:
    from ._common_crypto_cffi import CommonCrypto
except (FFIEngineError, ImportError):
    from ._common_crypto_ctypes import CommonCrypto


__all__ = [
    'CommonCrypto',
    'CommonCryptoConst',
]


class CommonCryptoConst():
    kCCPBKDF2 = 2
    kCCPRFHmacAlgSHA1 = 1
    kCCPRFHmacAlgSHA224 = 2
    kCCPRFHmacAlgSHA256 = 3
    kCCPRFHmacAlgSHA384 = 4
    kCCPRFHmacAlgSHA512 = 5
