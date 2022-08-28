# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from .._errors import pretty_message
from .._ffi import (
    buffer_from_bytes,
    bytes_from_buffer,
    deref,
    new,
    null,
    pointer_set,
    struct,
    struct_bytes,
    unwrap,
    write_to_buffer,
)
from .util import rand_bytes
from .. import backend
from .._types import type_name, byte_cls

_backend = backend()

if _backend == 'winlegacy':
    from ._advapi32 import advapi32, Advapi32Const, handle_error, open_context_handle, close_context_handle
else:
    from ._cng import bcrypt, BcryptConst, handle_error, open_alg_handle, close_alg_handle


__all__ = [
    'aes_cbc_no_padding_decrypt',
    'aes_cbc_no_padding_encrypt',
    'aes_cbc_pkcs7_decrypt',
    'aes_cbc_pkcs7_encrypt',
    'des_cbc_pkcs5_decrypt',
    'des_cbc_pkcs5_encrypt',
    'rc2_cbc_pkcs5_decrypt',
    'rc2_cbc_pkcs5_encrypt',
    'rc4_decrypt',
    'rc4_encrypt',
    'tripledes_cbc_pkcs5_decrypt',
    'tripledes_cbc_pkcs5_encrypt',
]


def aes_cbc_no_padding_encrypt(key, data, iv):
    """
    Encrypts plaintext using AES in CBC mode with a 128, 192 or 256 bit key and
    no padding. This means the ciphertext must be an exact multiple of 16 bytes
    long.

    :param key:
        The encryption key - a byte string either 16, 24 or 32 bytes long

    :param data:
        The plaintext - a byte string

    :param iv:
        The initialization vector - either a byte string 16-bytes long or None
        to generate an IV

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A tuple of two byte strings (iv, ciphertext)
    """

    if len(key) not in [16, 24, 32]:
        raise ValueError(pretty_message(
            '''
            key must be either 16, 24 or 32 bytes (128, 192 or 256 bits)
            long - is %s
            ''',
            len(key)
        ))

    if not iv:
        iv = rand_bytes(16)
    elif len(iv) != 16:
        raise ValueError(pretty_message(
            '''
            iv must be 16 bytes long - is %s
            ''',
            len(iv)
        ))

    if len(data) % 16 != 0:
        raise ValueError(pretty_message(
            '''
            data must be a multiple of 16 bytes long - is %s
            ''',
            len(data)
        ))

    return (iv, _encrypt('aes', key, data, iv, False))


def aes_cbc_no_padding_decrypt(key, data, iv):
    """
    Decrypts AES ciphertext in CBC mode using a 128, 192 or 256 bit key and no
    padding.

    :param key:
        The encryption key - a byte string either 16, 24 or 32 bytes long

    :param data:
        The ciphertext - a byte string

    :param iv:
        The initialization vector - a byte string 16-bytes long

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the plaintext
    """

    if len(key) not in [16, 24, 32]:
        raise ValueError(pretty_message(
            '''
            key must be either 16, 24 or 32 bytes (128, 192 or 256 bits)
            long - is %s
            ''',
            len(key)
        ))

    if len(iv) != 16:
        raise ValueError(pretty_message(
            '''
            iv must be 16 bytes long - is %s
            ''',
            len(iv)
        ))

    return _decrypt('aes', key, data, iv, False)


def aes_cbc_pkcs7_encrypt(key, data, iv):
    """
    Encrypts plaintext using AES in CBC mode with a 128, 192 or 256 bit key and
    PKCS#7 padding.

    :param key:
        The encryption key - a byte string either 16, 24 or 32 bytes long

    :param data:
        The plaintext - a byte string

    :param iv:
        The initialization vector - either a byte string 16-bytes long or None
        to generate an IV

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A tuple of two byte strings (iv, ciphertext)
    """

    if len(key) not in [16, 24, 32]:
        raise ValueError(pretty_message(
            '''
            key must be either 16, 24 or 32 bytes (128, 192 or 256 bits)
            long - is %s
            ''',
            len(key)
        ))

    if not iv:
        iv = rand_bytes(16)
    elif len(iv) != 16:
        raise ValueError(pretty_message(
            '''
            iv must be 16 bytes long - is %s
            ''',
            len(iv)
        ))

    return (iv, _encrypt('aes', key, data, iv, True))


def aes_cbc_pkcs7_decrypt(key, data, iv):
    """
    Decrypts AES ciphertext in CBC mode using a 128, 192 or 256 bit key

    :param key:
        The encryption key - a byte string either 16, 24 or 32 bytes long

    :param data:
        The ciphertext - a byte string

    :param iv:
        The initialization vector - a byte string 16-bytes long

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the plaintext
    """

    if len(key) not in [16, 24, 32]:
        raise ValueError(pretty_message(
            '''
            key must be either 16, 24 or 32 bytes (128, 192 or 256 bits)
            long - is %s
            ''',
            len(key)
        ))

    if len(iv) != 16:
        raise ValueError(pretty_message(
            '''
            iv must be 16 bytes long - is %s
            ''',
            len(iv)
        ))

    return _decrypt('aes', key, data, iv, True)


def rc4_encrypt(key, data):
    """
    Encrypts plaintext using RC4 with a 40-128 bit key

    :param key:
        The encryption key - a byte string 5-16 bytes long

    :param data:
        The plaintext - a byte string

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the ciphertext
    """

    if len(key) < 5 or len(key) > 16:
        raise ValueError(pretty_message(
            '''
            key must be 5 to 16 bytes (40 to 128 bits) long - is %s
            ''',
            len(key)
        ))

    return _encrypt('rc4', key, data, None, None)


def rc4_decrypt(key, data):
    """
    Decrypts RC4 ciphertext using a 40-128 bit key

    :param key:
        The encryption key - a byte string 5-16 bytes long

    :param data:
        The ciphertext - a byte string

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the plaintext
    """

    if len(key) < 5 or len(key) > 16:
        raise ValueError(pretty_message(
            '''
            key must be 5 to 16 bytes (40 to 128 bits) long - is %s
            ''',
            len(key)
        ))

    return _decrypt('rc4', key, data, None, None)


def rc2_cbc_pkcs5_encrypt(key, data, iv):
    """
    Encrypts plaintext using RC2 with a 64 bit key

    :param key:
        The encryption key - a byte string 8 bytes long

    :param data:
        The plaintext - a byte string

    :param iv:
        The 8-byte initialization vector to use - a byte string - set as None
        to generate an appropriate one

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A tuple of two byte strings (iv, ciphertext)
    """

    if len(key) < 5 or len(key) > 16:
        raise ValueError(pretty_message(
            '''
            key must be 5 to 16 bytes (40 to 128 bits) long - is %s
            ''',
            len(key)
        ))

    if not iv:
        iv = rand_bytes(8)
    elif len(iv) != 8:
        raise ValueError(pretty_message(
            '''
            iv must be 8 bytes long - is %s
            ''',
            len(iv)
        ))

    return (iv, _encrypt('rc2', key, data, iv, True))


def rc2_cbc_pkcs5_decrypt(key, data, iv):
    """
    Decrypts RC2 ciphertext using a 64 bit key

    :param key:
        The encryption key - a byte string 8 bytes long

    :param data:
        The ciphertext - a byte string

    :param iv:
        The initialization vector used for encryption - a byte string

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the plaintext
    """

    if len(key) < 5 or len(key) > 16:
        raise ValueError(pretty_message(
            '''
            key must be 5 to 16 bytes (40 to 128 bits) long - is %s
            ''',
            len(key)
        ))

    if len(iv) != 8:
        raise ValueError(pretty_message(
            '''
            iv must be 8 bytes long - is %s
            ''',
            len(iv)
        ))

    return _decrypt('rc2', key, data, iv, True)


def tripledes_cbc_pkcs5_encrypt(key, data, iv):
    """
    Encrypts plaintext using 3DES in either 2 or 3 key mode

    :param key:
        The encryption key - a byte string 16 or 24 bytes long (2 or 3 key mode)

    :param data:
        The plaintext - a byte string

    :param iv:
        The 8-byte initialization vector to use - a byte string - set as None
        to generate an appropriate one

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A tuple of two byte strings (iv, ciphertext)
    """

    if len(key) != 16 and len(key) != 24:
        raise ValueError(pretty_message(
            '''
            key must be 16 bytes (2 key) or 24 bytes (3 key) long - is %s
            ''',
            len(key)
        ))

    if not iv:
        iv = rand_bytes(8)
    elif len(iv) != 8:
        raise ValueError(pretty_message(
            '''
            iv must be 8 bytes long - is %s
            ''',
            len(iv)
        ))

    cipher = 'tripledes_3key'
    if len(key) == 16:
        cipher = 'tripledes_2key'

    return (iv, _encrypt(cipher, key, data, iv, True))


def tripledes_cbc_pkcs5_decrypt(key, data, iv):
    """
    Decrypts 3DES ciphertext in either 2 or 3 key mode

    :param key:
        The encryption key - a byte string 16 or 24 bytes long (2 or 3 key mode)

    :param data:
        The ciphertext - a byte string

    :param iv:
        The initialization vector used for encryption - a byte string

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the plaintext
    """

    if len(key) != 16 and len(key) != 24:
        raise ValueError(pretty_message(
            '''
            key must be 16 bytes (2 key) or 24 bytes (3 key) long - is %s
            ''',
            len(key)
        ))

    if len(iv) != 8:
        raise ValueError(pretty_message(
            '''
            iv must be 8 bytes long - is %s
            ''',
            len(iv)
        ))

    cipher = 'tripledes_3key'
    if len(key) == 16:
        cipher = 'tripledes_2key'

    return _decrypt(cipher, key, data, iv, True)


def des_cbc_pkcs5_encrypt(key, data, iv):
    """
    Encrypts plaintext using DES with a 56 bit key

    :param key:
        The encryption key - a byte string 8 bytes long (includes error
        correction bits)

    :param data:
        The plaintext - a byte string

    :param iv:
        The 8-byte initialization vector to use - a byte string - set as None
        to generate an appropriate one

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A tuple of two byte strings (iv, ciphertext)
    """

    if len(key) != 8:
        raise ValueError(pretty_message(
            '''
            key must be 8 bytes (56 bits + 8 parity bits) long - is %s
            ''',
            len(key)
        ))

    if not iv:
        iv = rand_bytes(8)
    elif len(iv) != 8:
        raise ValueError(pretty_message(
            '''
            iv must be 8 bytes long - is %s
            ''',
            len(iv)
        ))

    return (iv, _encrypt('des', key, data, iv, True))


def des_cbc_pkcs5_decrypt(key, data, iv):
    """
    Decrypts DES ciphertext using a 56 bit key

    :param key:
        The encryption key - a byte string 8 bytes long (includes error
        correction bits)

    :param data:
        The ciphertext - a byte string

    :param iv:
        The initialization vector used for encryption - a byte string

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the plaintext
    """

    if len(key) != 8:
        raise ValueError(pretty_message(
            '''
            key must be 8 bytes (56 bits + 8 parity bits) long - is %s
            ''',
            len(key)
        ))

    if len(iv) != 8:
        raise ValueError(pretty_message(
            '''
            iv must be 8 bytes long - is %s
            ''',
            len(iv)
        ))

    return _decrypt('des', key, data, iv, True)


def _advapi32_create_handles(cipher, key, iv):
    """
    Creates an HCRYPTPROV and HCRYPTKEY for symmetric encryption/decryption. The
    HCRYPTPROV must be released by close_context_handle() and the
    HCRYPTKEY must be released by advapi32.CryptDestroyKey() when done.

    :param cipher:
        A unicode string of "aes", "des", "tripledes_2key", "tripledes_3key",
        "rc2", "rc4"

    :param key:
        A byte string of the symmetric key

    :param iv:
        The initialization vector - a byte string - unused for RC4

    :return:
        A tuple of (HCRYPTPROV, HCRYPTKEY)
    """

    context_handle = None

    if cipher == 'aes':
        algorithm_id = {
            16: Advapi32Const.CALG_AES_128,
            24: Advapi32Const.CALG_AES_192,
            32: Advapi32Const.CALG_AES_256,
        }[len(key)]
    else:
        algorithm_id = {
            'des': Advapi32Const.CALG_DES,
            'tripledes_2key': Advapi32Const.CALG_3DES_112,
            'tripledes_3key': Advapi32Const.CALG_3DES,
            'rc2': Advapi32Const.CALG_RC2,
            'rc4': Advapi32Const.CALG_RC4,
        }[cipher]

    provider = Advapi32Const.MS_ENH_RSA_AES_PROV
    context_handle = open_context_handle(provider, verify_only=False)

    blob_header_pointer = struct(advapi32, 'BLOBHEADER')
    blob_header = unwrap(blob_header_pointer)
    blob_header.bType = Advapi32Const.PLAINTEXTKEYBLOB
    blob_header.bVersion = Advapi32Const.CUR_BLOB_VERSION
    blob_header.reserved = 0
    blob_header.aiKeyAlg = algorithm_id

    blob_struct_pointer = struct(advapi32, 'PLAINTEXTKEYBLOB')
    blob_struct = unwrap(blob_struct_pointer)
    blob_struct.hdr = blob_header
    blob_struct.dwKeySize = len(key)

    blob = struct_bytes(blob_struct_pointer) + key

    flags = 0
    if cipher in set(['rc2', 'rc4']) and len(key) == 5:
        flags = Advapi32Const.CRYPT_NO_SALT

    key_handle_pointer = new(advapi32, 'HCRYPTKEY *')
    res = advapi32.CryptImportKey(
        context_handle,
        blob,
        len(blob),
        null(),
        flags,
        key_handle_pointer
    )
    handle_error(res)

    key_handle = unwrap(key_handle_pointer)

    if cipher == 'rc2':
        buf = new(advapi32, 'DWORD *', len(key) * 8)
        res = advapi32.CryptSetKeyParam(
            key_handle,
            Advapi32Const.KP_EFFECTIVE_KEYLEN,
            buf,
            0
        )
        handle_error(res)

    if cipher != 'rc4':
        res = advapi32.CryptSetKeyParam(
            key_handle,
            Advapi32Const.KP_IV,
            iv,
            0
        )
        handle_error(res)

        buf = new(advapi32, 'DWORD *', Advapi32Const.CRYPT_MODE_CBC)
        res = advapi32.CryptSetKeyParam(
            key_handle,
            Advapi32Const.KP_MODE,
            buf,
            0
        )
        handle_error(res)

        buf = new(advapi32, 'DWORD *', Advapi32Const.PKCS5_PADDING)
        res = advapi32.CryptSetKeyParam(
            key_handle,
            Advapi32Const.KP_PADDING,
            buf,
            0
        )
        handle_error(res)

    return (context_handle, key_handle)


def _bcrypt_create_key_handle(cipher, key):
    """
    Creates a BCRYPT_KEY_HANDLE for symmetric encryption/decryption. The
    handle must be released by bcrypt.BCryptDestroyKey() when done.

    :param cipher:
        A unicode string of "aes", "des", "tripledes_2key", "tripledes_3key",
        "rc2", "rc4"

    :param key:
        A byte string of the symmetric key

    :return:
        A BCRYPT_KEY_HANDLE
    """

    alg_handle = None

    alg_constant = {
        'aes': BcryptConst.BCRYPT_AES_ALGORITHM,
        'des': BcryptConst.BCRYPT_DES_ALGORITHM,
        'tripledes_2key': BcryptConst.BCRYPT_3DES_112_ALGORITHM,
        'tripledes_3key': BcryptConst.BCRYPT_3DES_ALGORITHM,
        'rc2': BcryptConst.BCRYPT_RC2_ALGORITHM,
        'rc4': BcryptConst.BCRYPT_RC4_ALGORITHM,
    }[cipher]

    try:
        alg_handle = open_alg_handle(alg_constant)
        blob_type = BcryptConst.BCRYPT_KEY_DATA_BLOB

        blob_struct_pointer = struct(bcrypt, 'BCRYPT_KEY_DATA_BLOB_HEADER')
        blob_struct = unwrap(blob_struct_pointer)
        blob_struct.dwMagic = BcryptConst.BCRYPT_KEY_DATA_BLOB_MAGIC
        blob_struct.dwVersion = BcryptConst.BCRYPT_KEY_DATA_BLOB_VERSION1
        blob_struct.cbKeyData = len(key)

        blob = struct_bytes(blob_struct_pointer) + key

        if cipher == 'rc2':
            buf = new(bcrypt, 'DWORD *', len(key) * 8)
            res = bcrypt.BCryptSetProperty(
                alg_handle,
                BcryptConst.BCRYPT_EFFECTIVE_KEY_LENGTH,
                buf,
                4,
                0
            )
            handle_error(res)

        key_handle_pointer = new(bcrypt, 'BCRYPT_KEY_HANDLE *')
        res = bcrypt.BCryptImportKey(
            alg_handle,
            null(),
            blob_type,
            key_handle_pointer,
            null(),
            0,
            blob,
            len(blob),
            0
        )
        handle_error(res)

        return unwrap(key_handle_pointer)

    finally:
        if alg_handle:
            close_alg_handle(alg_handle)


def _encrypt(cipher, key, data, iv, padding):
    """
    Encrypts plaintext

    :param cipher:
        A unicode string of "aes", "des", "tripledes_2key", "tripledes_3key",
        "rc2", "rc4"

    :param key:
        The encryption key - a byte string 5-16 bytes long

    :param data:
        The plaintext - a byte string

    :param iv:
        The initialization vector - a byte string - unused for RC4

    :param padding:
        Boolean, if padding should be used - unused for RC4

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the ciphertext
    """

    if not isinstance(key, byte_cls):
        raise TypeError(pretty_message(
            '''
            key must be a byte string, not %s
            ''',
            type_name(key)
        ))

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    if cipher != 'rc4' and not isinstance(iv, byte_cls):
        raise TypeError(pretty_message(
            '''
            iv must be a byte string, not %s
            ''',
            type_name(iv)
        ))

    if cipher != 'rc4' and not padding:
        # AES in CBC mode can be allowed with no padding if
        # the data is an exact multiple of the block size
        if not (cipher == 'aes' and len(data) % 16 == 0):
            raise ValueError('padding must be specified')

    if _backend == 'winlegacy':
        return _advapi32_encrypt(cipher, key, data, iv, padding)
    return _bcrypt_encrypt(cipher, key, data, iv, padding)


def _advapi32_encrypt(cipher, key, data, iv, padding):
    """
    Encrypts plaintext via CryptoAPI

    :param cipher:
        A unicode string of "aes", "des", "tripledes_2key", "tripledes_3key",
        "rc2", "rc4"

    :param key:
        The encryption key - a byte string 5-16 bytes long

    :param data:
        The plaintext - a byte string

    :param iv:
        The initialization vector - a byte string - unused for RC4

    :param padding:
        Boolean, if padding should be used - unused for RC4

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the ciphertext
    """

    context_handle = None
    key_handle = None

    try:
        context_handle, key_handle = _advapi32_create_handles(cipher, key, iv)

        out_len = new(advapi32, 'DWORD *', len(data))
        res = advapi32.CryptEncrypt(
            key_handle,
            null(),
            True,
            0,
            null(),
            out_len,
            0
        )
        handle_error(res)

        buffer_len = deref(out_len)
        buffer = buffer_from_bytes(buffer_len)
        write_to_buffer(buffer, data)

        pointer_set(out_len, len(data))
        res = advapi32.CryptEncrypt(
            key_handle,
            null(),
            True,
            0,
            buffer,
            out_len,
            buffer_len
        )
        handle_error(res)

        output = bytes_from_buffer(buffer, deref(out_len))

        # Remove padding when not required. CryptoAPI doesn't support this, so
        # we just manually remove it.
        if cipher == 'aes' and not padding and len(output) == len(data) + 16:
            output = output[:-16]

        return output

    finally:
        if key_handle:
            advapi32.CryptDestroyKey(key_handle)
        if context_handle:
            close_context_handle(context_handle)


def _bcrypt_encrypt(cipher, key, data, iv, padding):
    """
    Encrypts plaintext via CNG

    :param cipher:
        A unicode string of "aes", "des", "tripledes_2key", "tripledes_3key",
        "rc2", "rc4"

    :param key:
        The encryption key - a byte string 5-16 bytes long

    :param data:
        The plaintext - a byte string

    :param iv:
        The initialization vector - a byte string - unused for RC4

    :param padding:
        Boolean, if padding should be used - unused for RC4

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the ciphertext
    """

    key_handle = None

    try:
        key_handle = _bcrypt_create_key_handle(cipher, key)

        if iv is None:
            iv_len = 0
        else:
            iv_len = len(iv)

        flags = 0
        if padding is True:
            flags = BcryptConst.BCRYPT_BLOCK_PADDING

        out_len = new(bcrypt, 'ULONG *')
        res = bcrypt.BCryptEncrypt(
            key_handle,
            data,
            len(data),
            null(),
            null(),
            0,
            null(),
            0,
            out_len,
            flags
        )
        handle_error(res)

        buffer_len = deref(out_len)
        buffer = buffer_from_bytes(buffer_len)
        iv_buffer = buffer_from_bytes(iv) if iv else null()

        res = bcrypt.BCryptEncrypt(
            key_handle,
            data,
            len(data),
            null(),
            iv_buffer,
            iv_len,
            buffer,
            buffer_len,
            out_len,
            flags
        )
        handle_error(res)

        return bytes_from_buffer(buffer, deref(out_len))

    finally:
        if key_handle:
            bcrypt.BCryptDestroyKey(key_handle)


def _decrypt(cipher, key, data, iv, padding):
    """
    Decrypts AES/RC4/RC2/3DES/DES ciphertext

    :param cipher:
        A unicode string of "aes", "des", "tripledes_2key", "tripledes_3key",
        "rc2", "rc4"

    :param key:
        The encryption key - a byte string 5-16 bytes long

    :param data:
        The ciphertext - a byte string

    :param iv:
        The initialization vector - a byte string - unused for RC4

    :param padding:
        Boolean, if padding should be used - unused for RC4

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the plaintext
    """

    if not isinstance(key, byte_cls):
        raise TypeError(pretty_message(
            '''
            key must be a byte string, not %s
            ''',
            type_name(key)
        ))

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    if cipher != 'rc4' and not isinstance(iv, byte_cls):
        raise TypeError(pretty_message(
            '''
            iv must be a byte string, not %s
            ''',
            type_name(iv)
        ))

    if cipher not in set(['rc4', 'aes']) and not padding:
        raise ValueError('padding must be specified')

    if _backend == 'winlegacy':
        return _advapi32_decrypt(cipher, key, data, iv, padding)
    return _bcrypt_decrypt(cipher, key, data, iv, padding)


def _advapi32_decrypt(cipher, key, data, iv, padding):
    """
    Decrypts AES/RC4/RC2/3DES/DES ciphertext via CryptoAPI

    :param cipher:
        A unicode string of "aes", "des", "tripledes_2key", "tripledes_3key",
        "rc2", "rc4"

    :param key:
        The encryption key - a byte string 5-16 bytes long

    :param data:
        The ciphertext - a byte string

    :param iv:
        The initialization vector - a byte string - unused for RC4

    :param padding:
        Boolean, if padding should be used - unused for RC4

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the plaintext
    """

    context_handle = None
    key_handle = None

    try:
        context_handle, key_handle = _advapi32_create_handles(cipher, key, iv)

        if cipher == 'aes' and not padding and len(data) % 16 != 0:
            raise ValueError('Invalid data - ciphertext length must be a multiple of 16')

        buffer = buffer_from_bytes(data)
        out_len = new(advapi32, 'DWORD *', len(data))
        res = advapi32.CryptDecrypt(
            key_handle,
            null(),
            # To skip padding, we have to tell the API that this is not
            # the final block
            False if cipher == 'aes' and not padding else True,
            0,
            buffer,
            out_len
        )
        handle_error(res)

        return bytes_from_buffer(buffer, deref(out_len))

    finally:
        if key_handle:
            advapi32.CryptDestroyKey(key_handle)
        if context_handle:
            close_context_handle(context_handle)


def _bcrypt_decrypt(cipher, key, data, iv, padding):
    """
    Decrypts AES/RC4/RC2/3DES/DES ciphertext via CNG

    :param cipher:
        A unicode string of "aes", "des", "tripledes_2key", "tripledes_3key",
        "rc2", "rc4"

    :param key:
        The encryption key - a byte string 5-16 bytes long

    :param data:
        The ciphertext - a byte string

    :param iv:
        The initialization vector - a byte string - unused for RC4

    :param padding:
        Boolean, if padding should be used - unused for RC4

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the plaintext
    """

    key_handle = None

    try:
        key_handle = _bcrypt_create_key_handle(cipher, key)

        if iv is None:
            iv_len = 0
        else:
            iv_len = len(iv)

        flags = 0
        if padding is True:
            flags = BcryptConst.BCRYPT_BLOCK_PADDING

        out_len = new(bcrypt, 'ULONG *')
        res = bcrypt.BCryptDecrypt(
            key_handle,
            data,
            len(data),
            null(),
            null(),
            0,
            null(),
            0,
            out_len,
            flags
        )
        handle_error(res)

        buffer_len = deref(out_len)
        buffer = buffer_from_bytes(buffer_len)
        iv_buffer = buffer_from_bytes(iv) if iv else null()

        res = bcrypt.BCryptDecrypt(
            key_handle,
            data,
            len(data),
            null(),
            iv_buffer,
            iv_len,
            buffer,
            buffer_len,
            out_len,
            flags
        )
        handle_error(res)

        return bytes_from_buffer(buffer, deref(out_len))

    finally:
        if key_handle:
            bcrypt.BCryptDestroyKey(key_handle)
