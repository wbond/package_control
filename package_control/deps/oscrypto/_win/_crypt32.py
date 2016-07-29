# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from ._decode import _try_decode
from .._ffi import FFIEngineError, buffer_from_bytes
from .._types import str_cls

try:
    from ._crypt32_cffi import crypt32, get_error
except (FFIEngineError, ImportError):
    from ._crypt32_ctypes import crypt32, get_error


__all__ = [
    'crypt32',
    'Crypt32Const',
    'handle_error',
]


def handle_error(result):
    """
    Extracts the last Windows error message into a python unicode string

    :param result:
        A function result, 0 or None indicates failure

    :return:
        A unicode string error message
    """

    if result:
        return

    _, error_string = get_error()

    if not isinstance(error_string, str_cls):
        error_string = _try_decode(error_string)

    raise OSError(error_string)


class Crypt32Const():
    X509_ASN_ENCODING = 1

    ERROR_INSUFFICIENT_BUFFER = 122
    CERT_FIND_PROP_ONLY_ENHKEY_USAGE_FLAG = 0x4
    CRYPT_E_NOT_FOUND = -2146885628

    CERT_STORE_PROV_MEMORY = b'Memory'
    CERT_STORE_CREATE_NEW_FLAG = 0x00002000
    CERT_STORE_ADD_USE_EXISTING = 2
    USAGE_MATCH_TYPE_OR = 1
    CERT_CHAIN_POLICY_SSL = 4
    AUTHTYPE_SERVER = 2
    CERT_CHAIN_POLICY_ALLOW_UNKNOWN_CA_FLAG = 0x00000010
    CERT_CHAIN_POLICY_IGNORE_ALL_REV_UNKNOWN_FLAGS = 0x00000F00
    CERT_CHAIN_CACHE_END_CERT = 1
    CERT_CHAIN_REVOCATION_CHECK_CACHE_ONLY = 0x80000000

    TRUST_E_CERT_SIGNATURE = 0x80096004

    CERT_E_EXPIRED = 0x800B0101
    CERT_E_ROLE = 0x800B0103
    CERT_E_PURPOSE = 0x800B0106
    CERT_E_UNTRUSTEDROOT = 0x800B0109
    CERT_E_CN_NO_MATCH = 0x800B010F
    CRYPT_E_REVOKED = 0x80092010

    PKIX_KP_SERVER_AUTH = buffer_from_bytes(b"1.3.6.1.5.5.7.3.1\x00")
    SERVER_GATED_CRYPTO = buffer_from_bytes(b"1.3.6.1.4.1.311.10.3.3\x00")
    SGC_NETSCAPE = buffer_from_bytes(b"2.16.840.1.113730.4.1\x00")
