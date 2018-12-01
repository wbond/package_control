# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from ctypes.util import find_library
from ctypes import CDLL, CFUNCTYPE, POINTER, c_void_p, c_char_p, c_int, c_size_t, c_long

from .. import _backend_config
from .._ffi import FFIEngineError
from ..errors import LibraryNotFoundError
from ._libcrypto import libcrypto_version_info


__all__ = [
    'libssl',
]


libssl_path = _backend_config().get('libssl_path')
if libssl_path is None:
    libssl_path = find_library('ssl')
if not libssl_path:
    raise LibraryNotFoundError('The library libssl could not be found')

libssl = CDLL(libssl_path, use_errno=True)

P_SSL_METHOD = POINTER(c_void_p)
P_SSL_CTX = POINTER(c_void_p)
P_SSL_SESSION = POINTER(c_void_p)
P_SSL = POINTER(c_void_p)
P_BIO_METHOD = POINTER(c_void_p)
P_BIO = POINTER(c_void_p)
X509 = c_void_p
P_X509 = POINTER(X509)
P_X509_STORE = POINTER(c_void_p)
P_X509_STORE_CTX = POINTER(c_void_p)
_STACK = c_void_p
P_STACK = POINTER(_STACK)

try:
    if libcrypto_version_info < (1, 1):
        libssl.sk_num.argtypes = [P_STACK]
        libssl.sk_num.restype = c_int

        libssl.sk_value.argtypes = [P_STACK, c_int]
        libssl.sk_value.restype = P_X509

        libssl.SSL_library_init.argtypes = []
        libssl.SSL_library_init.restype = c_int

        libssl.OPENSSL_add_all_algorithms_noconf.argtypes = []
        libssl.OPENSSL_add_all_algorithms_noconf.restype = None

        libssl.SSLv23_method.argtypes = []
        libssl.SSLv23_method.restype = P_SSL_METHOD

    else:
        libssl.OPENSSL_sk_num.argtypes = [P_STACK]
        libssl.OPENSSL_sk_num.restype = c_int

        libssl.OPENSSL_sk_value.argtypes = [P_STACK, c_int]
        libssl.OPENSSL_sk_value.restype = P_X509

        libssl.TLS_method.argtypes = []
        libssl.TLS_method.restype = P_SSL_METHOD

    libssl.BIO_s_mem.argtypes = []
    libssl.BIO_s_mem.restype = P_BIO_METHOD

    libssl.BIO_new.argtypes = [
        P_BIO_METHOD
    ]
    libssl.BIO_new.restype = P_BIO

    libssl.BIO_free.argtypes = [
        P_BIO
    ]
    libssl.BIO_free.restype = c_int

    libssl.BIO_read.argtypes = [
        P_BIO,
        c_char_p,
        c_int
    ]
    libssl.BIO_read.restype = c_int

    libssl.BIO_write.argtypes = [
        P_BIO,
        c_char_p,
        c_int
    ]
    libssl.BIO_write.restype = c_int

    libssl.BIO_ctrl_pending.argtypes = [
        P_BIO
    ]
    libssl.BIO_ctrl_pending.restype = c_size_t

    libssl.SSL_CTX_new.argtypes = [
        P_SSL_METHOD
    ]
    libssl.SSL_CTX_new.restype = P_SSL_CTX

    libssl.SSL_CTX_set_timeout.argtypes = [
        P_SSL_CTX,
        c_long
    ]
    libssl.SSL_CTX_set_timeout.restype = c_long

    verify_callback = CFUNCTYPE(c_int, c_int, P_X509_STORE_CTX)
    setattr(libssl, 'verify_callback', verify_callback)

    libssl.SSL_CTX_set_verify.argtypes = [
        P_SSL_CTX,
        c_int,
        POINTER(verify_callback)
    ]
    libssl.SSL_CTX_set_verify.restype = None

    libssl.SSL_CTX_set_default_verify_paths.argtypes = [
        P_SSL_CTX
    ]
    libssl.SSL_CTX_set_default_verify_paths.restype = c_int

    libssl.SSL_CTX_load_verify_locations.argtypes = [
        P_SSL_CTX,
        c_char_p,
        c_char_p
    ]
    libssl.SSL_CTX_load_verify_locations.restype = c_int

    libssl.SSL_get_verify_result.argtypes = [
        P_SSL
    ]
    libssl.SSL_get_verify_result.restype = c_long

    libssl.SSL_CTX_get_cert_store.argtypes = [
        P_SSL_CTX
    ]
    libssl.SSL_CTX_get_cert_store.restype = P_X509_STORE

    libssl.X509_STORE_add_cert.argtypes = [
        P_X509_STORE,
        P_X509
    ]
    libssl.X509_STORE_add_cert.restype = c_int

    libssl.SSL_CTX_set_cipher_list.argtypes = [
        P_SSL_CTX,
        c_char_p
    ]
    libssl.SSL_CTX_set_cipher_list.restype = c_int

    libssl.SSL_CTX_ctrl.arg_types = [
        P_SSL_CTX,
        c_int,
        c_long,
        c_void_p
    ]
    libssl.SSL_CTX_ctrl.restype = c_long

    libssl.SSL_CTX_free.argtypes = [
        P_SSL_CTX
    ]
    libssl.SSL_CTX_free.restype = None

    libssl.SSL_new.argtypes = [
        P_SSL_CTX
    ]
    libssl.SSL_new.restype = P_SSL

    libssl.SSL_free.argtypes = [
        P_SSL
    ]
    libssl.SSL_free.restype = None

    libssl.SSL_set_bio.argtypes = [
        P_SSL,
        P_BIO,
        P_BIO
    ]
    libssl.SSL_set_bio.restype = None

    libssl.SSL_ctrl.arg_types = [
        P_SSL,
        c_int,
        c_long,
        c_void_p
    ]
    libssl.SSL_ctrl.restype = c_long

    libssl.SSL_get_peer_cert_chain.argtypes = [
        P_SSL
    ]
    libssl.SSL_get_peer_cert_chain.restype = P_STACK

    libssl.SSL_get1_session.argtypes = [
        P_SSL
    ]
    libssl.SSL_get1_session.restype = P_SSL_SESSION

    libssl.SSL_set_session.argtypes = [
        P_SSL,
        P_SSL_SESSION
    ]
    libssl.SSL_set_session.restype = c_int

    libssl.SSL_SESSION_free.argtypes = [
        P_SSL_SESSION
    ]
    libssl.SSL_SESSION_free.restype = None

    libssl.SSL_set_connect_state.argtypes = [
        P_SSL
    ]
    libssl.SSL_set_connect_state.restype = None

    libssl.SSL_do_handshake.argtypes = [
        P_SSL
    ]
    libssl.SSL_do_handshake.restype = c_int

    libssl.SSL_get_error.argtypes = [
        P_SSL,
        c_int
    ]
    libssl.SSL_get_error.restype = c_int

    libssl.SSL_get_version.argtypes = [
        P_SSL
    ]
    libssl.SSL_get_version.restype = c_char_p

    libssl.SSL_read.argtypes = [
        P_SSL,
        c_char_p,
        c_int
    ]
    libssl.SSL_read.restype = c_int

    libssl.SSL_write.argtypes = [
        P_SSL,
        c_char_p,
        c_int
    ]
    libssl.SSL_write.restype = c_int

    libssl.SSL_pending.argtypes = [
        P_SSL
    ]
    libssl.SSL_pending.restype = c_int

    libssl.SSL_shutdown.argtypes = [
        P_SSL
    ]
    libssl.SSL_shutdown.restype = c_int

except (AttributeError):
    raise FFIEngineError('Error initializing ctypes')

setattr(libssl, '_STACK', _STACK)
setattr(libssl, 'X509', X509)
