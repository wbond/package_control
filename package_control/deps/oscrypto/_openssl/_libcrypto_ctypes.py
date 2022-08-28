# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import re

from ctypes import CDLL, c_void_p, c_char_p, c_int, c_ulong, c_uint, c_long, c_size_t, POINTER

from .. import _backend_config
from .._errors import pretty_message
from .._ffi import FFIEngineError, get_library
from ..errors import LibraryNotFoundError


__all__ = [
    'is_libressl',
    'libcrypto',
    'libressl_version',
    'libressl_version_info',
    'version',
    'version_info',
]


libcrypto_path = _backend_config().get('libcrypto_path')
if libcrypto_path is None:
    libcrypto_path = get_library('crypto', 'libcrypto.dylib', '42')
if not libcrypto_path:
    raise LibraryNotFoundError('The library libcrypto could not be found')

libcrypto = CDLL(libcrypto_path, use_errno=True)

try:
    libcrypto.SSLeay_version.argtypes = [c_int]
    libcrypto.SSLeay_version.restype = c_char_p
    version_string = libcrypto.SSLeay_version(0).decode('utf-8')
except (AttributeError):
    libcrypto.OpenSSL_version.argtypes = [c_int]
    libcrypto.OpenSSL_version.restype = c_char_p
    version_string = libcrypto.OpenSSL_version(0).decode('utf-8')

is_libressl = 'LibreSSL' in version_string

version_match = re.search('\\b(\\d\\.\\d\\.\\d[a-z]*)\\b', version_string)
if not version_match:
    version_match = re.search('(?<=LibreSSL )(\\d\\.\\d(\\.\\d)?)\\b', version_string)
if not version_match:
    raise LibraryNotFoundError('Error detecting the version of libcrypto')
version = version_match.group(1)
version_parts = re.sub('(\\d)([a-z]+)', '\\1.\\2', version).split('.')
version_info = tuple(int(part) if part.isdigit() else part for part in version_parts)

# LibreSSL is compatible with libcrypto from OpenSSL 1.0.1
libressl_version = ''
libressl_version_info = tuple()
if is_libressl:
    libressl_version = version
    libressl_version_info = version_info
    version = '1.0.1'
    version_info = (1, 0, 1)

if version_info < (0, 9, 8):
    raise LibraryNotFoundError(pretty_message(
        '''
        OpenSSL versions older than 0.9.8 are not supported - found version %s
        ''',
        version
    ))

P_EVP_CIPHER_CTX = c_void_p
P_EVP_CIPHER = c_void_p

P_EVP_MD_CTX = c_void_p
P_EVP_MD = c_void_p

P_ENGINE = c_void_p
OSSL_PROVIDER = c_void_p
OSSL_LIB_CTX = c_void_p

P_EVP_PKEY = c_void_p
EVP_PKEY_CTX = c_void_p
P_EVP_PKEY_CTX = POINTER(c_void_p)
P_X509 = POINTER(c_void_p)
P_DH = c_void_p
P_RSA = c_void_p
P_DSA = c_void_p
P_EC_KEY = c_void_p
P_BN_GENCB = c_void_p
BIGNUM = c_void_p
P_BIGNUM = POINTER(BIGNUM)

p_int = POINTER(c_int)
p_uint = POINTER(c_uint)

try:
    if version_info < (1, 1):
        libcrypto.ERR_load_crypto_strings.argtypes = []
        libcrypto.ERR_load_crypto_strings.restype = None

        libcrypto.ERR_free_strings.argtypes = []
        libcrypto.ERR_free_strings.restype = None

    if version_info >= (3, ):
        libcrypto.OSSL_PROVIDER_available.argtypes = [OSSL_LIB_CTX, c_char_p]
        libcrypto.OSSL_PROVIDER_available.restype = c_int

        libcrypto.OSSL_PROVIDER_load.argtypes = [OSSL_LIB_CTX, c_char_p]
        libcrypto.OSSL_PROVIDER_load.restype = POINTER(OSSL_PROVIDER)

    libcrypto.ERR_get_error.argtypes = []
    libcrypto.ERR_get_error.restype = c_ulong

    libcrypto.ERR_peek_error.argtypes = []
    libcrypto.ERR_peek_error.restype = c_ulong

    libcrypto.ERR_error_string.argtypes = [
        c_ulong,
        c_char_p
    ]
    libcrypto.ERR_error_string.restype = c_char_p

    libcrypto.OPENSSL_config.argtypes = [
        c_char_p
    ]
    libcrypto.OPENSSL_config.restype = None

    # This allocates the memory and inits
    libcrypto.EVP_CIPHER_CTX_new.argtype = []
    libcrypto.EVP_CIPHER_CTX_new.restype = P_EVP_CIPHER_CTX

    libcrypto.EVP_CIPHER_CTX_set_key_length.argtypes = [
        P_EVP_CIPHER_CTX,
        c_int
    ]
    libcrypto.EVP_CIPHER_CTX_set_key_length.restype = c_int

    libcrypto.EVP_CIPHER_CTX_set_padding.argtypes = [
        P_EVP_CIPHER_CTX,
        c_int
    ]
    libcrypto.EVP_CIPHER_CTX_set_padding.restype = c_int

    libcrypto.EVP_CIPHER_CTX_ctrl.argtypes = [
        P_EVP_CIPHER_CTX,
        c_int,
        c_int,
        c_void_p
    ]
    libcrypto.EVP_CIPHER_CTX_ctrl.restype = c_int

    # This cleans up and frees
    libcrypto.EVP_CIPHER_CTX_free.argtypes = [
        P_EVP_CIPHER_CTX
    ]
    libcrypto.EVP_CIPHER_CTX_free.restype = None

    libcrypto.EVP_aes_128_cbc.argtypes = []
    libcrypto.EVP_aes_128_cbc.restype = P_EVP_CIPHER

    libcrypto.EVP_aes_192_cbc.argtypes = []
    libcrypto.EVP_aes_192_cbc.restype = P_EVP_CIPHER

    libcrypto.EVP_aes_256_cbc.argtypes = []
    libcrypto.EVP_aes_256_cbc.restype = P_EVP_CIPHER

    libcrypto.EVP_des_cbc.argtypes = []
    libcrypto.EVP_des_cbc.restype = P_EVP_CIPHER

    libcrypto.EVP_des_ede_cbc.argtypes = []
    libcrypto.EVP_des_ede_cbc.restype = P_EVP_CIPHER

    libcrypto.EVP_des_ede3_cbc.argtypes = []
    libcrypto.EVP_des_ede3_cbc.restype = P_EVP_CIPHER

    libcrypto.EVP_rc4.argtypes = []
    libcrypto.EVP_rc4.restype = P_EVP_CIPHER

    libcrypto.EVP_rc2_cbc.argtypes = []
    libcrypto.EVP_rc2_cbc.restype = P_EVP_CIPHER

    libcrypto.EVP_EncryptInit_ex.argtypes = [
        P_EVP_CIPHER_CTX,
        P_EVP_CIPHER,
        P_ENGINE,
        c_char_p,
        c_char_p
    ]
    libcrypto.EVP_EncryptInit_ex.restype = c_int

    libcrypto.EVP_EncryptUpdate.argtypes = [
        P_EVP_CIPHER_CTX,
        c_char_p,
        p_int,
        c_char_p,
        c_int
    ]
    libcrypto.EVP_EncryptUpdate.restype = c_int

    libcrypto.EVP_EncryptFinal_ex.argtypes = [
        P_EVP_CIPHER_CTX,
        c_char_p,
        p_int
    ]
    libcrypto.EVP_EncryptFinal_ex.restype = c_int

    libcrypto.EVP_DecryptInit_ex.argtypes = [
        P_EVP_CIPHER_CTX,
        P_EVP_CIPHER,
        P_ENGINE,
        c_char_p,
        c_char_p
    ]
    libcrypto.EVP_DecryptInit_ex.restype = c_int

    libcrypto.EVP_DecryptUpdate.argtypes = [
        P_EVP_CIPHER_CTX,
        c_char_p,
        p_int,
        c_char_p,
        c_int
    ]
    libcrypto.EVP_DecryptUpdate.restype = c_int

    libcrypto.EVP_DecryptFinal_ex.argtypes = [
        P_EVP_CIPHER_CTX,
        c_char_p,
        p_int
    ]
    libcrypto.EVP_DecryptFinal_ex.restype = c_int

    libcrypto.d2i_AutoPrivateKey.argtypes = [
        POINTER(P_EVP_PKEY),
        POINTER(c_char_p),
        c_int
    ]
    libcrypto.d2i_AutoPrivateKey.restype = P_EVP_PKEY

    libcrypto.d2i_PUBKEY.argtypes = [
        POINTER(P_EVP_PKEY),
        POINTER(c_char_p),
        c_int
    ]
    libcrypto.d2i_PUBKEY.restype = P_EVP_PKEY

    libcrypto.i2d_PUBKEY.argtypes = [
        P_EVP_PKEY,
        POINTER(c_char_p)
    ]
    libcrypto.i2d_PUBKEY.restype = c_int

    libcrypto.d2i_X509.argtypes = [
        POINTER(P_X509),
        POINTER(c_char_p),
        c_int
    ]
    libcrypto.d2i_X509.restype = P_X509

    libcrypto.i2d_X509.argtypes = [
        P_X509,
        POINTER(c_char_p)
    ]
    libcrypto.i2d_X509.restype = c_int

    libcrypto.X509_get_pubkey.argtypes = [
        P_X509
    ]
    libcrypto.X509_get_pubkey.restype = P_EVP_PKEY

    libcrypto.X509_free.argtypes = [
        P_X509
    ]
    libcrypto.X509_free.restype = None

    libcrypto.EVP_PKEY_free.argtypes = [
        P_EVP_PKEY
    ]
    libcrypto.EVP_PKEY_free.restype = None

    if version_info < (1, 1):
        libcrypto.EVP_MD_CTX_create.argtypes = []
        libcrypto.EVP_MD_CTX_create.restype = P_EVP_MD_CTX

        libcrypto.EVP_MD_CTX_destroy.argtypes = [
            P_EVP_MD_CTX
        ]
        libcrypto.EVP_MD_CTX_destroy.restype = None
    else:
        libcrypto.EVP_MD_CTX_new.argtypes = []
        libcrypto.EVP_MD_CTX_new.restype = P_EVP_MD_CTX

        libcrypto.EVP_MD_CTX_free.argtypes = [
            P_EVP_MD_CTX
        ]
        libcrypto.EVP_MD_CTX_free.restype = None

    libcrypto.EVP_md5.argtypes = []
    libcrypto.EVP_md5.restype = P_EVP_MD

    libcrypto.EVP_sha1.argtypes = []
    libcrypto.EVP_sha1.restype = P_EVP_MD

    libcrypto.EVP_sha224.argtypes = []
    libcrypto.EVP_sha224.restype = P_EVP_MD

    libcrypto.EVP_sha256.argtypes = []
    libcrypto.EVP_sha256.restype = P_EVP_MD

    libcrypto.EVP_sha384.argtypes = []
    libcrypto.EVP_sha384.restype = P_EVP_MD

    libcrypto.EVP_sha512.argtypes = []
    libcrypto.EVP_sha512.restype = P_EVP_MD

    if version_info < (3, 0):
        libcrypto.EVP_PKEY_size.argtypes = [
            P_EVP_PKEY
        ]
        libcrypto.EVP_PKEY_size.restype = c_int
    else:
        libcrypto.EVP_PKEY_get_size.argtypes = [
            P_EVP_PKEY
        ]
        libcrypto.EVP_PKEY_get_size.restype = c_int

    libcrypto.EVP_PKEY_get1_RSA.argtypes = [
        P_EVP_PKEY
    ]
    libcrypto.EVP_PKEY_get1_RSA.restype = P_RSA

    libcrypto.RSA_free.argtypes = [
        P_RSA
    ]
    libcrypto.RSA_free.restype = None

    libcrypto.RSA_public_encrypt.argtypes = [
        c_int,
        c_char_p,
        c_char_p,
        P_RSA,
        c_int
    ]
    libcrypto.RSA_public_encrypt.restype = c_int

    libcrypto.RSA_private_encrypt.argtypes = [
        c_int,
        c_char_p,
        c_char_p,
        P_RSA,
        c_int
    ]
    libcrypto.RSA_private_encrypt.restype = c_int

    libcrypto.RSA_public_decrypt.argtypes = [
        c_int,
        c_char_p,
        c_char_p,
        P_RSA,
        c_int
    ]
    libcrypto.RSA_public_decrypt.restype = c_int

    libcrypto.RSA_private_decrypt.argtypes = [
        c_int,
        c_char_p,
        c_char_p,
        P_RSA,
        c_int
    ]
    libcrypto.RSA_private_decrypt.restype = c_int

    libcrypto.EVP_DigestUpdate.argtypes = [
        P_EVP_MD_CTX,
        c_char_p,
        c_uint
    ]
    libcrypto.EVP_DigestUpdate.restype = c_int

    libcrypto.PKCS12_key_gen_uni.argtypes = [
        c_char_p,
        c_int,
        c_char_p,
        c_int,
        c_int,
        c_int,
        c_int,
        c_char_p,
        c_void_p
    ]
    libcrypto.PKCS12_key_gen_uni.restype = c_int

    libcrypto.BN_free.argtypes = [
        P_BIGNUM
    ]
    libcrypto.BN_free.restype = None

    libcrypto.BN_dec2bn.argtypes = [
        POINTER(P_BIGNUM),
        c_char_p
    ]
    libcrypto.BN_dec2bn.restype = c_int

    libcrypto.DH_new.argtypes = []
    libcrypto.DH_new.restype = P_DH

    libcrypto.DH_generate_parameters_ex.argtypes = [
        P_DH,
        c_int,
        c_int,
        P_BN_GENCB
    ]
    libcrypto.DH_generate_parameters_ex.restype = c_int

    libcrypto.i2d_DHparams.argtypes = [
        P_DH,
        POINTER(c_char_p)
    ]
    libcrypto.i2d_DHparams.restype = c_int

    libcrypto.DH_free.argtypes = [
        P_DH
    ]
    libcrypto.DH_free.restype = None

    libcrypto.RSA_new.argtypes = []
    libcrypto.RSA_new.restype = P_RSA

    libcrypto.RSA_generate_key_ex.argtypes = [
        P_RSA,
        c_int,
        P_BIGNUM,
        P_BN_GENCB
    ]
    libcrypto.RSA_generate_key_ex.restype = c_int

    libcrypto.i2d_RSAPublicKey.argtypes = [
        P_RSA,
        POINTER(c_char_p)
    ]
    libcrypto.i2d_RSAPublicKey.restype = c_int

    libcrypto.i2d_RSAPrivateKey.argtypes = [
        P_RSA,
        POINTER(c_char_p)
    ]
    libcrypto.i2d_RSAPrivateKey.restype = c_int

    libcrypto.RSA_free.argtypes = [
        P_RSA
    ]
    libcrypto.RSA_free.restype = None

    libcrypto.DSA_new.argtypes = []
    libcrypto.DSA_new.restype = P_DSA

    libcrypto.DSA_generate_parameters_ex.argtypes = [
        P_DSA,
        c_int,
        c_char_p,
        c_int,
        POINTER(c_int),
        POINTER(c_ulong),
        P_BN_GENCB
    ]
    libcrypto.DSA_generate_parameters_ex.restype = c_int

    libcrypto.DSA_generate_key.argtypes = [
        P_DSA
    ]
    libcrypto.DSA_generate_key.restype = c_int

    libcrypto.i2d_DSA_PUBKEY.argtypes = [
        P_DSA,
        POINTER(c_char_p)
    ]
    libcrypto.i2d_DSA_PUBKEY.restype = c_int

    libcrypto.i2d_DSAPrivateKey.argtypes = [
        P_DSA,
        POINTER(c_char_p)
    ]
    libcrypto.i2d_DSAPrivateKey.restype = c_int

    libcrypto.DSA_free.argtypes = [
        P_DSA
    ]
    libcrypto.DSA_free.restype = None

    libcrypto.EC_KEY_new_by_curve_name.argtypes = [
        c_int
    ]
    libcrypto.EC_KEY_new_by_curve_name.restype = P_EC_KEY

    libcrypto.EC_KEY_generate_key.argtypes = [
        P_EC_KEY
    ]
    libcrypto.EC_KEY_generate_key.restype = c_int

    libcrypto.EC_KEY_set_asn1_flag.argtypes = [
        P_EC_KEY,
        c_int
    ]
    libcrypto.EC_KEY_set_asn1_flag.restype = None

    libcrypto.i2d_ECPrivateKey.argtypes = [
        P_EC_KEY,
        POINTER(c_char_p)
    ]
    libcrypto.i2d_ECPrivateKey.restype = c_int

    libcrypto.i2o_ECPublicKey.argtypes = [
        P_EC_KEY,
        POINTER(c_char_p)
    ]
    libcrypto.i2o_ECPublicKey.restype = c_int

    libcrypto.EC_KEY_free.argtypes = [
        P_EC_KEY
    ]
    libcrypto.EC_KEY_free.restype = None

    if version_info < (1,):
        P_DSA_SIG = c_void_p
        P_ECDSA_SIG = c_void_p

        libcrypto.DSA_do_sign.argtypes = [
            c_char_p,
            c_int,
            P_DSA
        ]
        libcrypto.DSA_do_sign.restype = P_DSA_SIG

        libcrypto.ECDSA_do_sign.argtypes = [
            c_char_p,
            c_int,
            P_EC_KEY
        ]
        libcrypto.ECDSA_do_sign.restype = P_ECDSA_SIG

        libcrypto.d2i_DSA_SIG.argtypes = [
            POINTER(P_DSA_SIG),
            POINTER(c_char_p),
            c_long
        ]
        libcrypto.d2i_DSA_SIG.restype = P_DSA_SIG

        libcrypto.d2i_ECDSA_SIG.argtypes = [
            POINTER(P_ECDSA_SIG),
            POINTER(c_char_p),
            c_long
        ]
        libcrypto.d2i_ECDSA_SIG.restype = P_ECDSA_SIG

        libcrypto.i2d_DSA_SIG.argtypes = [
            P_DSA_SIG,
            POINTER(c_char_p)
        ]
        libcrypto.i2d_DSA_SIG.restype = c_int

        libcrypto.i2d_ECDSA_SIG.argtypes = [
            P_ECDSA_SIG,
            POINTER(c_char_p)
        ]
        libcrypto.i2d_ECDSA_SIG.restype = c_int

        libcrypto.DSA_do_verify.argtypes = [
            c_char_p,
            c_int,
            P_DSA_SIG,
            P_DSA
        ]
        libcrypto.DSA_do_verify.restype = c_int

        libcrypto.ECDSA_do_verify.argtypes = [
            c_char_p,
            c_int,
            P_ECDSA_SIG,
            P_EC_KEY
        ]
        libcrypto.ECDSA_do_verify.restype = c_int

        libcrypto.DSA_SIG_free.argtypes = [
            P_DSA_SIG
        ]
        libcrypto.DSA_SIG_free.restype = None

        libcrypto.ECDSA_SIG_free.argtypes = [
            P_ECDSA_SIG
        ]
        libcrypto.ECDSA_SIG_free.restype = None

        libcrypto.EVP_PKEY_get1_DSA.argtypes = [
            P_EVP_PKEY
        ]
        libcrypto.EVP_PKEY_get1_DSA.restype = P_DSA

        libcrypto.EVP_PKEY_get1_EC_KEY.argtypes = [
            P_EVP_PKEY
        ]
        libcrypto.EVP_PKEY_get1_EC_KEY.restype = P_EC_KEY

        libcrypto.RSA_verify_PKCS1_PSS.argtypes = [
            P_RSA,
            c_char_p,
            P_EVP_MD,
            c_char_p,
            c_int
        ]
        libcrypto.RSA_verify_PKCS1_PSS.restype = c_int

        libcrypto.RSA_padding_add_PKCS1_PSS.argtypes = [
            P_RSA,
            c_char_p,
            c_char_p,
            P_EVP_MD,
            c_int
        ]
        libcrypto.RSA_padding_add_PKCS1_PSS.restype = c_int

        libcrypto.EVP_DigestInit_ex.argtypes = [
            P_EVP_MD_CTX,
            P_EVP_MD,
            P_ENGINE
        ]
        libcrypto.EVP_DigestInit_ex.restype = c_int

        libcrypto.EVP_SignFinal.argtypes = [
            P_EVP_MD_CTX,
            c_char_p,
            p_uint,
            P_EVP_PKEY
        ]
        libcrypto.EVP_SignFinal.restype = c_int

        libcrypto.EVP_VerifyFinal.argtypes = [
            P_EVP_MD_CTX,
            c_char_p,
            c_uint,
            P_EVP_PKEY
        ]
        libcrypto.EVP_VerifyFinal.restype = c_int

        libcrypto.EVP_MD_CTX_set_flags.argtypes = [
            P_EVP_MD_CTX,
            c_int
        ]
        libcrypto.EVP_MD_CTX_set_flags.restype = None

    else:
        libcrypto.PKCS5_PBKDF2_HMAC.argtypes = [
            c_char_p,
            c_int,
            c_char_p,
            c_int,
            c_int,
            P_EVP_MD,
            c_int,
            c_char_p
        ]
        libcrypto.PKCS5_PBKDF2_HMAC.restype = c_int

        libcrypto.EVP_DigestSignInit.argtypes = [
            P_EVP_MD_CTX,
            POINTER(P_EVP_PKEY_CTX),
            P_EVP_MD,
            P_ENGINE,
            P_EVP_PKEY
        ]
        libcrypto.EVP_DigestSignInit.restype = c_int

        libcrypto.EVP_DigestSignFinal.argtypes = [
            P_EVP_MD_CTX,
            c_char_p,
            POINTER(c_size_t)
        ]
        libcrypto.EVP_DigestSignFinal.restype = c_int

        libcrypto.EVP_DigestVerifyInit.argtypes = [
            P_EVP_MD_CTX,
            POINTER(P_EVP_PKEY_CTX),
            P_EVP_MD,
            P_ENGINE,
            P_EVP_PKEY
        ]
        libcrypto.EVP_DigestVerifyInit.restype = c_int

        libcrypto.EVP_DigestVerifyFinal.argtypes = [
            P_EVP_MD_CTX,
            c_char_p,
            c_size_t
        ]
        libcrypto.EVP_DigestVerifyFinal.restype = c_int

        libcrypto.EVP_PKEY_CTX_ctrl.argtypes = [
            P_EVP_PKEY_CTX,
            c_int,
            c_int,
            c_int,
            c_int,
            c_void_p
        ]
        libcrypto.EVP_PKEY_CTX_ctrl.restype = c_int

except (AttributeError):
    raise FFIEngineError('Error initializing ctypes')


setattr(libcrypto, 'EVP_PKEY_CTX', EVP_PKEY_CTX)
setattr(libcrypto, 'BIGNUM', BIGNUM)
