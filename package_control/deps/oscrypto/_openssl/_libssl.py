# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from .._ffi import FFIEngineError

# Initialize OpenSSL
from ._libcrypto import libcrypto_version_info

try:
    from ._libssl_cffi import libssl
except (FFIEngineError, ImportError):
    from ._libssl_ctypes import libssl


__all__ = [
    'libssl',
    'LibsslConst',
]


if libcrypto_version_info < (1, 1):
    libssl.SSL_library_init()
# Enables SHA2 algorithms on 0.9.8n and older
if libcrypto_version_info < (1, 0):
    libssl.OPENSSL_add_all_algorithms_noconf()


class LibsslConst():
    SSL_CTRL_OPTIONS = 32
    SSL_CTRL_SET_SESS_CACHE_MODE = 44

    SSL_VERIFY_NONE = 0
    SSL_VERIFY_PEER = 1

    SSL_ST_OK = 3

    SSL_ERROR_WANT_READ = 2
    SSL_ERROR_WANT_WRITE = 3
    SSL_ERROR_ZERO_RETURN = 6

    SSL_OP_NO_SSLv2 = 0x01000000
    SSL_OP_NO_SSLv3 = 0x02000000
    SSL_OP_NO_TLSv1 = 0x04000000
    SSL_OP_NO_TLSv1_2 = 0x08000000
    SSL_OP_NO_TLSv1_1 = 0x10000000

    SSL_SESS_CACHE_CLIENT = 0x0001

    SSL_R_NO_SHARED_CIPHER = 193

    SSL_F_SSL3_CHECK_CERT_AND_ALGORITHM = 130
    SSL_F_SSL3_GET_SERVER_CERTIFICATE = 144
    SSL_R_CERTIFICATE_VERIFY_FAILED = 134
    SSL_R_UNKNOWN_PROTOCOL = 252
    SSL_R_DH_KEY_TOO_SMALL = 372

    # OpenSSL 1.1.0
    SSL_F_TLS_PROCESS_SKE_DHE = 419
    SSL_F_SSL3_GET_RECORD = 143
    SSL_R_WRONG_VERSION_NUMBER = 267
    SSL_F_TLS_PROCESS_SERVER_CERTIFICATE = 367

    # OpenSSL < 1.1.0
    SSL_F_SSL23_GET_SERVER_HELLO = 119
    SSL_F_SSL3_READ_BYTES = 148
    SSL_R_SSLV3_ALERT_HANDSHAKE_FAILURE = 1040

    SSL_CTRL_SET_TLSEXT_HOSTNAME = 55
    TLSEXT_NAMETYPE_host_name = 0

    X509_V_ERR_UNABLE_TO_GET_ISSUER_CERT_LOCALLY = 20
    X509_V_ERR_SELF_SIGNED_CERT_IN_CHAIN = 19
    X509_V_ERR_DEPTH_ZERO_SELF_SIGNED_CERT = 18

    X509_V_ERR_CERT_NOT_YET_VALID = 9
    X509_V_ERR_CERT_HAS_EXPIRED = 10


if libcrypto_version_info >= (1, 1, 0):
    LibsslConst.SSL_R_DH_KEY_TOO_SMALL = 394
