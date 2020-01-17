# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from .. import ffi
from .._ffi import new, null, unwrap

if ffi() == 'cffi':
    from ._cng_cffi import bcrypt
else:
    from ._cng_ctypes import bcrypt


__all__ = [
    'bcrypt',
    'BcryptConst',
    'close_alg_handle',
    'handle_error',
    'open_alg_handle',
]


def open_alg_handle(constant, flags=0):
    handle_pointer = new(bcrypt, 'BCRYPT_ALG_HANDLE *')
    res = bcrypt.BCryptOpenAlgorithmProvider(handle_pointer, constant, null(), flags)
    handle_error(res)

    return unwrap(handle_pointer)


def close_alg_handle(handle):
    res = bcrypt.BCryptCloseAlgorithmProvider(handle, 0)
    handle_error(res)


def handle_error(error_num):
    """
    Extracts the last Windows error message into a python unicode string

    :param error_num:
        The number to get the error string for

    :return:
        A unicode string error message
    """

    if error_num == 0:
        return

    messages = {
        BcryptConst.STATUS_NOT_FOUND: 'The object was not found',
        BcryptConst.STATUS_INVALID_PARAMETER: 'An invalid parameter was passed to a service or function',
        BcryptConst.STATUS_NO_MEMORY: (
            'Not enough virtual memory or paging file quota is available to complete the specified operation'
        ),
        BcryptConst.STATUS_INVALID_HANDLE: 'An invalid HANDLE was specified',
        BcryptConst.STATUS_INVALID_SIGNATURE: 'The cryptographic signature is invalid',
        BcryptConst.STATUS_NOT_SUPPORTED: 'The request is not supported',
        BcryptConst.STATUS_BUFFER_TOO_SMALL: 'The buffer is too small to contain the entry',
        BcryptConst.STATUS_INVALID_BUFFER_SIZE: 'The size of the buffer is invalid for the specified operation',
    }

    output = 'NTSTATUS error 0x%0.2X' % error_num

    if error_num is not None and error_num in messages:
        output += ': ' + messages[error_num]

    raise OSError(output)


class BcryptConst():
    BCRYPT_RNG_ALGORITHM = 'RNG'

    BCRYPT_KEY_LENGTH = 'KeyLength'
    BCRYPT_EFFECTIVE_KEY_LENGTH = 'EffectiveKeyLength'

    BCRYPT_RSAPRIVATE_BLOB = 'RSAPRIVATEBLOB'
    BCRYPT_RSAFULLPRIVATE_BLOB = 'RSAFULLPRIVATEBLOB'
    BCRYPT_RSAPUBLIC_BLOB = 'RSAPUBLICBLOB'
    BCRYPT_DSA_PRIVATE_BLOB = 'DSAPRIVATEBLOB'
    BCRYPT_DSA_PUBLIC_BLOB = 'DSAPUBLICBLOB'
    BCRYPT_ECCPRIVATE_BLOB = 'ECCPRIVATEBLOB'
    BCRYPT_ECCPUBLIC_BLOB = 'ECCPUBLICBLOB'

    BCRYPT_RSAPUBLIC_MAGIC = 0x31415352
    BCRYPT_RSAPRIVATE_MAGIC = 0x32415352
    BCRYPT_RSAFULLPRIVATE_MAGIC = 0x33415352

    BCRYPT_DSA_PUBLIC_MAGIC = 0x42505344
    BCRYPT_DSA_PRIVATE_MAGIC = 0x56505344
    BCRYPT_DSA_PUBLIC_MAGIC_V2 = 0x32425044
    BCRYPT_DSA_PRIVATE_MAGIC_V2 = 0x32565044

    DSA_HASH_ALGORITHM_SHA1 = 0
    DSA_HASH_ALGORITHM_SHA256 = 1
    DSA_HASH_ALGORITHM_SHA512 = 2

    DSA_FIPS186_2 = 0
    DSA_FIPS186_3 = 1

    BCRYPT_NO_KEY_VALIDATION = 8

    BCRYPT_ECDSA_PUBLIC_P256_MAGIC = 0x31534345
    BCRYPT_ECDSA_PRIVATE_P256_MAGIC = 0x32534345
    BCRYPT_ECDSA_PUBLIC_P384_MAGIC = 0x33534345
    BCRYPT_ECDSA_PRIVATE_P384_MAGIC = 0x34534345
    BCRYPT_ECDSA_PUBLIC_P521_MAGIC = 0x35534345
    BCRYPT_ECDSA_PRIVATE_P521_MAGIC = 0x36534345

    STATUS_SUCCESS = 0x00000000
    STATUS_NOT_FOUND = 0xC0000225
    STATUS_INVALID_PARAMETER = 0xC000000D
    STATUS_NO_MEMORY = 0xC0000017
    STATUS_INVALID_HANDLE = 0xC0000008
    STATUS_INVALID_SIGNATURE = 0xC000A000
    STATUS_NOT_SUPPORTED = 0xC00000BB
    STATUS_BUFFER_TOO_SMALL = 0xC0000023
    STATUS_INVALID_BUFFER_SIZE = 0xC0000206

    BCRYPT_KEY_DATA_BLOB_MAGIC = 0x4d42444b
    BCRYPT_KEY_DATA_BLOB_VERSION1 = 0x00000001
    BCRYPT_KEY_DATA_BLOB = 'KeyDataBlob'

    BCRYPT_PAD_PKCS1 = 0x00000002
    BCRYPT_PAD_OAEP = 0x00000004
    BCRYPT_PAD_PSS = 0x00000008

    BCRYPT_3DES_ALGORITHM = '3DES'
    BCRYPT_3DES_112_ALGORITHM = '3DES_112'
    BCRYPT_AES_ALGORITHM = 'AES'
    BCRYPT_DES_ALGORITHM = 'DES'
    BCRYPT_RC2_ALGORITHM = 'RC2'
    BCRYPT_RC4_ALGORITHM = 'RC4'

    BCRYPT_DSA_ALGORITHM = 'DSA'
    BCRYPT_ECDSA_P256_ALGORITHM = 'ECDSA_P256'
    BCRYPT_ECDSA_P384_ALGORITHM = 'ECDSA_P384'
    BCRYPT_ECDSA_P521_ALGORITHM = 'ECDSA_P521'
    BCRYPT_RSA_ALGORITHM = 'RSA'

    BCRYPT_MD5_ALGORITHM = 'MD5'
    BCRYPT_SHA1_ALGORITHM = 'SHA1'
    BCRYPT_SHA256_ALGORITHM = 'SHA256'
    BCRYPT_SHA384_ALGORITHM = 'SHA384'
    BCRYPT_SHA512_ALGORITHM = 'SHA512'

    BCRYPT_ALG_HANDLE_HMAC_FLAG = 0x00000008

    BCRYPT_BLOCK_PADDING = 0x00000001
