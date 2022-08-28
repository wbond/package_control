# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from .. import ffi
from .._ffi import buffer_from_bytes, byte_string_from_buffer, null
from .._types import str_cls

if ffi() == 'cffi':
    from ._libcrypto_cffi import (
        libcrypto,
        version as libcrypto_version,
        version_info as libcrypto_version_info
    )
else:
    from ._libcrypto_ctypes import (
        libcrypto,
        version as libcrypto_version,
        version_info as libcrypto_version_info
    )


__all__ = [
    'handle_openssl_error',
    'libcrypto',
    'libcrypto_legacy_support',
    'libcrypto_version',
    'libcrypto_version_info',
    'LibcryptoConst',
    'peek_openssl_error',
]


_encoding = 'utf-8'
_fallback_encodings = ['utf-8', 'cp1252']


if libcrypto_version_info < (1, 1):
    libcrypto.ERR_load_crypto_strings()
libcrypto.OPENSSL_config(null())


# This enables legacy algorithms in OpenSSL 3.0, such as RC2, etc
# which are used by various tests and some old protocols and things
# like PKCS12
libcrypto_legacy_support = True
if libcrypto_version_info >= (3, ):
    if libcrypto.OSSL_PROVIDER_available(null(), "legacy".encode("ascii")):
        libcrypto.OSSL_PROVIDER_load(null(), "legacy".encode("ascii"))
    else:
        libcrypto_legacy_support = False


def _try_decode(value):

    try:
        return str_cls(value, _encoding)

    # If the "correct" encoding did not work, try some defaults, and then just
    # obliterate characters that we can't seen to decode properly
    except (UnicodeDecodeError):
        for encoding in _fallback_encodings:
            try:
                return str_cls(value, encoding, errors='strict')
            except (UnicodeDecodeError):
                pass

    return str_cls(value, errors='replace')


def handle_openssl_error(result, exception_class=None):
    """
    Checks if an error occurred, and if so throws an OSError containing the
    last OpenSSL error message

    :param result:
        An integer result code - 1 or greater indicates success

    :param exception_class:
        The exception class to use for the exception if an error occurred

    :raises:
        OSError - when an OpenSSL error occurs
    """

    if result > 0:
        return

    if exception_class is None:
        exception_class = OSError

    error_num = libcrypto.ERR_get_error()
    buffer = buffer_from_bytes(120)
    libcrypto.ERR_error_string(error_num, buffer)

    # Since we are dealing with a string, it is NULL terminated
    error_string = byte_string_from_buffer(buffer)

    raise exception_class(_try_decode(error_string))


def peek_openssl_error():
    """
    Peeks into the error stack and pulls out the lib, func and reason

    :return:
        A three-element tuple of integers (lib, func, reason)
    """

    error = libcrypto.ERR_peek_error()
    if libcrypto_version_info < (3, 0):
        lib = int((error >> 24) & 0xff)
        func = int((error >> 12) & 0xfff)
        reason = int(error & 0xfff)
    else:
        lib = int((error >> 23) & 0xff)
        # OpenSSL 3.0 removed ERR_GET_FUNC()
        func = 0
        reason = int(error & 0x7fffff)

    return (lib, func, reason)


class LibcryptoConst():
    EVP_CTRL_SET_RC2_KEY_BITS = 3

    SSLEAY_VERSION = 0

    RSA_PKCS1_PADDING = 1
    RSA_NO_PADDING = 3
    RSA_PKCS1_OAEP_PADDING = 4

    # OpenSSL 0.9.x
    EVP_MD_CTX_FLAG_PSS_MDLEN = -1

    # OpenSSL 1.x.x
    EVP_PKEY_CTRL_RSA_PADDING = 0x1001
    RSA_PKCS1_PSS_PADDING = 6
    EVP_PKEY_CTRL_RSA_PSS_SALTLEN = 0x1002
    EVP_PKEY_RSA = 6
    EVP_PKEY_OP_SIGN = 1 << 3
    EVP_PKEY_OP_VERIFY = 1 << 4

    NID_X9_62_prime256v1 = 415
    NID_secp384r1 = 715
    NID_secp521r1 = 716

    OPENSSL_EC_NAMED_CURVE = 1

    DH_GENERATOR_2 = 2
