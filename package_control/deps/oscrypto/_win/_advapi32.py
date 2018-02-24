# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import sys

from ._decode import _try_decode
from ..errors import SignatureError
from .._ffi import FFIEngineError, new, unwrap, null
from .._types import str_cls

try:
    from ._advapi32_cffi import advapi32, get_error
except (FFIEngineError, ImportError):
    from ._advapi32_ctypes import advapi32, get_error


__all__ = [
    'advapi32',
    'Advapi32Const',
    'handle_error',
]


_gwv = sys.getwindowsversion()
_win_version_info = (_gwv[0], _gwv[1])


def open_context_handle(provider, verify_only=True):
    if provider == Advapi32Const.MS_ENH_RSA_AES_PROV:
        provider_type = Advapi32Const.PROV_RSA_AES
    elif provider == Advapi32Const.MS_ENH_DSS_DH_PROV:
        provider_type = Advapi32Const.PROV_DSS_DH
    else:
        raise ValueError('Invalid provider specified: %s' % provider)

    # Ths DSS provider needs a container to allow importing and exporting
    # private keys, but all of the RSA stuff works fine with CRYPT_VERIFYCONTEXT
    if verify_only or provider != Advapi32Const.MS_ENH_DSS_DH_PROV:
        container_name = null()
        flags = Advapi32Const.CRYPT_VERIFYCONTEXT
    else:
        container_name = Advapi32Const.CONTAINER_NAME
        flags = Advapi32Const.CRYPT_NEWKEYSET

    context_handle_pointer = new(advapi32, 'HCRYPTPROV *')
    res = advapi32.CryptAcquireContextW(
        context_handle_pointer,
        container_name,
        provider,
        provider_type,
        flags
    )
    # If using the DSS provider and the container exists, just open it
    if not res and get_error()[0] == Advapi32Const.NTE_EXISTS:
        res = advapi32.CryptAcquireContextW(
            context_handle_pointer,
            container_name,
            provider,
            provider_type,
            0
        )
    handle_error(res)

    return unwrap(context_handle_pointer)


def close_context_handle(handle):
    res = advapi32.CryptReleaseContext(handle, 0)
    handle_error(res)


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

    code, error_string = get_error()

    if code == Advapi32Const.NTE_BAD_SIGNATURE:
        raise SignatureError('Signature is invalid')

    if not isinstance(error_string, str_cls):
        error_string = _try_decode(error_string)

    raise OSError(error_string)


class Advapi32Const():
    # Name we give to a container used to make DSA private key import/export work
    CONTAINER_NAME = 'oscrypto temporary DSS keyset'

    PROV_RSA_AES = 24
    PROV_DSS_DH = 13

    X509_PUBLIC_KEY_INFO = 8
    PKCS_PRIVATE_KEY_INFO = 44
    X509_DSS_SIGNATURE = 40
    CRYPT_NO_SALT = 0x00000010

    MS_ENH_DSS_DH_PROV = "Microsoft Enhanced DSS and Diffie-Hellman Cryptographic Provider"
    # This is the name for Windows Server 2003 and newer and Windows Vista and newer
    MS_ENH_RSA_AES_PROV = "Microsoft Enhanced RSA and AES Cryptographic Provider"

    CRYPT_EXPORTABLE = 1
    CRYPT_NEWKEYSET = 0x00000008
    CRYPT_VERIFYCONTEXT = 0xF0000000

    CALG_MD5 = 0x00008003
    CALG_SHA1 = 0x00008004
    CALG_SHA_256 = 0x0000800c
    CALG_SHA_384 = 0x0000800d
    CALG_SHA_512 = 0x0000800e

    CALG_RC2 = 0x00006602
    CALG_RC4 = 0x00006801
    CALG_DES = 0x00006601
    CALG_3DES_112 = 0x00006609
    CALG_3DES = 0x00006603
    CALG_AES_128 = 0x0000660e
    CALG_AES_192 = 0x0000660f
    CALG_AES_256 = 0x00006610

    CALG_DSS_SIGN = 0x00002200
    CALG_RSA_SIGN = 0x00002400
    CALG_RSA_KEYX = 0x0000a400

    CRYPT_MODE_CBC = 1

    PKCS5_PADDING = 1

    CUR_BLOB_VERSION = 2
    PUBLICKEYBLOB = 6
    PRIVATEKEYBLOB = 7
    PLAINTEXTKEYBLOB = 8

    KP_IV = 1
    KP_PADDING = 3
    KP_MODE = 4
    KP_EFFECTIVE_KEYLEN = 19

    CRYPT_OAEP = 0x00000040

    NTE_BAD_SIGNATURE = -2146893818  # 0x80090006
    NTE_EXISTS = -2146893809  # 0x8009000F
    AT_SIGNATURE = 2

    RSA1 = 0x31415352
    RSA2 = 0x32415352
    DSS1 = 0x31535344
    DSS2 = 0x32535344


if _win_version_info == (5, 1):
    # This is the Windows XP name for the provider
    Advapi32Const.MS_ENH_RSA_AES_PROV = "Microsoft Enhanced RSA and AES Cryptographic Provider (Prototype)"
