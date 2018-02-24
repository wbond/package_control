# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import math

from .._errors import pretty_message
from .._ffi import new, null, is_null, buffer_from_bytes, bytes_from_buffer, deref
from ._libcrypto import libcrypto, LibcryptoConst, handle_openssl_error
from ..util import rand_bytes
from .._types import type_name, byte_cls


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
        OSError - when an error is returned by OpenSSL

    :return:
        A tuple of two byte strings (iv, ciphertext)
    """

    cipher = _calculate_aes_cipher(key)

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

    return (iv, _encrypt(cipher, key, data, iv, False))


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
        OSError - when an error is returned by OpenSSL

    :return:
        A byte string of the plaintext
    """

    cipher = _calculate_aes_cipher(key)

    if len(iv) != 16:
        raise ValueError(pretty_message(
            '''
            iv must be 16 bytes long - is %s
            ''',
            len(iv)
        ))

    return _decrypt(cipher, key, data, iv, False)


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
        OSError - when an error is returned by OpenSSL

    :return:
        A tuple of two byte strings (iv, ciphertext)
    """

    cipher = _calculate_aes_cipher(key)

    if not iv:
        iv = rand_bytes(16)
    elif len(iv) != 16:
        raise ValueError(pretty_message(
            '''
            iv must be 16 bytes long - is %s
            ''',
            len(iv)
        ))

    return (iv, _encrypt(cipher, key, data, iv, True))


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
        OSError - when an error is returned by OpenSSL

    :return:
        A byte string of the plaintext
    """

    cipher = _calculate_aes_cipher(key)

    if len(iv) != 16:
        raise ValueError(pretty_message(
            '''
            iv must be 16 bytes long - is %s
            ''',
            len(iv)
        ))

    return _decrypt(cipher, key, data, iv, True)


def _calculate_aes_cipher(key):
    """
    Determines if the key is a valid AES 128, 192 or 256 key

    :param key:
        A byte string of the key to use

    :raises:
        ValueError - when an invalid key is provided

    :return:
        A unicode string of the AES variation - "aes128", "aes192" or "aes256"
    """

    if len(key) not in [16, 24, 32]:
        raise ValueError(pretty_message(
            '''
            key must be either 16, 24 or 32 bytes (128, 192 or 256 bits)
            long - is %s
            ''',
            len(key)
        ))

    if len(key) == 16:
        cipher = 'aes128'
    elif len(key) == 24:
        cipher = 'aes192'
    elif len(key) == 32:
        cipher = 'aes256'

    return cipher


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
        OSError - when an error is returned by OpenSSL

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
        OSError - when an error is returned by OpenSSL

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
    Encrypts plaintext using RC2 in CBC mode with a 40-128 bit key and PKCS#5
    padding.

    :param key:
        The encryption key - a byte string 8 bytes long

    :param data:
        The plaintext - a byte string

    :param iv:
        The initialization vector - a byte string 8-bytes long or None
        to generate an IV

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by OpenSSL

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
    Decrypts RC2 ciphertext ib CBC mode using a 40-128 bit key and PKCS#5
    padding.

    :param key:
        The encryption key - a byte string 8 bytes long

    :param data:
        The ciphertext - a byte string

    :param iv:
        The initialization vector - a byte string 8 bytes long

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by OpenSSL

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
    Encrypts plaintext using 3DES in CBC mode using either the 2 or 3 key
    variant (16 or 24 byte long key) and PKCS#5 padding.

    :param key:
        The encryption key - a byte string 16 or 24 bytes long (2 or 3 key mode)

    :param data:
        The plaintext - a byte string

    :param iv:
        The initialization vector - a byte string 8-bytes long or None
        to generate an IV

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by OpenSSL

    :return:
        A tuple of two byte strings (iv, ciphertext)
    """

    if len(key) != 16 and len(key) != 24:
        raise ValueError(pretty_message(
            '''
            key must be 16 bytes (2 key) or 24 bytes (3 key) long - %s
            ''',
            len(key)
        ))

    if not iv:
        iv = rand_bytes(8)
    elif len(iv) != 8:
        raise ValueError(pretty_message(
            '''
            iv must be 8 bytes long - %s
            ''',
            len(iv)
        ))

    cipher = 'tripledes_3key'
    # Expand 2-key to actual 24 byte byte string used by cipher
    if len(key) == 16:
        key = key + key[0:8]
        cipher = 'tripledes_2key'

    return (iv, _encrypt(cipher, key, data, iv, True))


def tripledes_cbc_pkcs5_decrypt(key, data, iv):
    """
    Decrypts 3DES ciphertext in CBC mode using either the 2 or 3 key variant
    (16 or 24 byte long key) and PKCS#5 padding.

    :param key:
        The encryption key - a byte string 16 or 24 bytes long (2 or 3 key mode)

    :param data:
        The ciphertext - a byte string

    :param iv:
        The initialization vector - a byte string 8-bytes long

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by OpenSSL

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
    # Expand 2-key to actual 24 byte byte string used by cipher
    if len(key) == 16:
        key = key + key[0:8]
        cipher = 'tripledes_2key'

    return _decrypt(cipher, key, data, iv, True)


def des_cbc_pkcs5_encrypt(key, data, iv):
    """
    Encrypts plaintext using DES in CBC mode with a 56 bit key and PKCS#5
    padding.

    :param key:
        The encryption key - a byte string 8 bytes long (includes error correction bits)

    :param data:
        The plaintext - a byte string

    :param iv:
        The initialization vector - a byte string 8-bytes long or None
        to generate an IV

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by OpenSSL

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
    Decrypts DES ciphertext in CBC mode using a 56 bit key and PKCS#5 padding.

    :param key:
        The encryption key - a byte string 8 bytes long (includes error correction bits)

    :param data:
        The ciphertext - a byte string

    :param iv:
        The initialization vector - a byte string 8-bytes long

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by OpenSSL

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


def _encrypt(cipher, key, data, iv, padding):
    """
    Encrypts plaintext

    :param cipher:
        A unicode string of "aes128", "aes192", "aes256", "des",
        "tripledes_2key", "tripledes_3key", "rc2", "rc4"

    :param key:
        The encryption key - a byte string 5-32 bytes long

    :param data:
        The plaintext - a byte string

    :param iv:
        The initialization vector - a byte string - unused for RC4

    :param padding:
        Boolean, if padding should be used - unused for RC4

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by OpenSSL

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
        raise ValueError('padding must be specified')

    evp_cipher_ctx = None

    try:
        evp_cipher_ctx = libcrypto.EVP_CIPHER_CTX_new()
        if is_null(evp_cipher_ctx):
            handle_openssl_error(0)

        evp_cipher, buffer_size = _setup_evp_encrypt_decrypt(cipher, data)

        if iv is None:
            iv = null()

        if cipher in set(['rc2', 'rc4']):
            res = libcrypto.EVP_EncryptInit_ex(evp_cipher_ctx, evp_cipher, null(), null(), null())
            handle_openssl_error(res)
            res = libcrypto.EVP_CIPHER_CTX_set_key_length(evp_cipher_ctx, len(key))
            handle_openssl_error(res)
            if cipher == 'rc2':
                res = libcrypto.EVP_CIPHER_CTX_ctrl(
                    evp_cipher_ctx,
                    LibcryptoConst.EVP_CTRL_SET_RC2_KEY_BITS,
                    len(key) * 8,
                    null()
                )
                handle_openssl_error(res)
            evp_cipher = null()

        res = libcrypto.EVP_EncryptInit_ex(evp_cipher_ctx, evp_cipher, null(), key, iv)
        handle_openssl_error(res)

        if padding is not None:
            res = libcrypto.EVP_CIPHER_CTX_set_padding(evp_cipher_ctx, int(padding))
            handle_openssl_error(res)

        buffer = buffer_from_bytes(buffer_size)
        output_length = new(libcrypto, 'int *')

        res = libcrypto.EVP_EncryptUpdate(evp_cipher_ctx, buffer, output_length, data, len(data))
        handle_openssl_error(res)

        output = bytes_from_buffer(buffer, deref(output_length))

        res = libcrypto.EVP_EncryptFinal_ex(evp_cipher_ctx, buffer, output_length)
        handle_openssl_error(res)

        output += bytes_from_buffer(buffer, deref(output_length))

        return output

    finally:
        if evp_cipher_ctx:
            libcrypto.EVP_CIPHER_CTX_free(evp_cipher_ctx)


def _decrypt(cipher, key, data, iv, padding):
    """
    Decrypts AES/RC4/RC2/3DES/DES ciphertext

    :param cipher:
        A unicode string of "aes128", "aes192", "aes256", "des",
        "tripledes_2key", "tripledes_3key", "rc2", "rc4"

    :param key:
        The encryption key - a byte string 5-32 bytes long

    :param data:
        The ciphertext - a byte string

    :param iv:
        The initialization vector - a byte string - unused for RC4

    :param padding:
        Boolean, if padding should be used - unused for RC4

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by OpenSSL

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

    if cipher != 'rc4' and padding is None:
        raise ValueError('padding must be specified')

    evp_cipher_ctx = None

    try:
        evp_cipher_ctx = libcrypto.EVP_CIPHER_CTX_new()
        if is_null(evp_cipher_ctx):
            handle_openssl_error(0)

        evp_cipher, buffer_size = _setup_evp_encrypt_decrypt(cipher, data)

        if iv is None:
            iv = null()

        if cipher in set(['rc2', 'rc4']):
            res = libcrypto.EVP_DecryptInit_ex(evp_cipher_ctx, evp_cipher, null(), null(), null())
            handle_openssl_error(res)
            res = libcrypto.EVP_CIPHER_CTX_set_key_length(evp_cipher_ctx, len(key))
            handle_openssl_error(res)
            if cipher == 'rc2':
                res = libcrypto.EVP_CIPHER_CTX_ctrl(
                    evp_cipher_ctx,
                    LibcryptoConst.EVP_CTRL_SET_RC2_KEY_BITS,
                    len(key) * 8,
                    null()
                )
                handle_openssl_error(res)
            evp_cipher = null()

        res = libcrypto.EVP_DecryptInit_ex(evp_cipher_ctx, evp_cipher, null(), key, iv)
        handle_openssl_error(res)

        if padding is not None:
            res = libcrypto.EVP_CIPHER_CTX_set_padding(evp_cipher_ctx, int(padding))
            handle_openssl_error(res)

        buffer = buffer_from_bytes(buffer_size)
        output_length = new(libcrypto, 'int *')

        res = libcrypto.EVP_DecryptUpdate(evp_cipher_ctx, buffer, output_length, data, len(data))
        handle_openssl_error(res)

        output = bytes_from_buffer(buffer, deref(output_length))

        res = libcrypto.EVP_DecryptFinal_ex(evp_cipher_ctx, buffer, output_length)
        handle_openssl_error(res)

        output += bytes_from_buffer(buffer, deref(output_length))

        return output

    finally:
        if evp_cipher_ctx:
            libcrypto.EVP_CIPHER_CTX_free(evp_cipher_ctx)


def _setup_evp_encrypt_decrypt(cipher, data):
    """
    Creates an EVP_CIPHER pointer object and determines the buffer size
    necessary for the parameter specified.

    :param evp_cipher_ctx:
        An EVP_CIPHER_CTX pointer

    :param cipher:
        A unicode string of "aes128", "aes192", "aes256", "des",
        "tripledes_2key", "tripledes_3key", "rc2", "rc4"

    :param key:
        The key byte string

    :param data:
        The plaintext or ciphertext as a byte string

    :param padding:
        If padding is to be used

    :return:
        A 2-element tuple with the first element being an EVP_CIPHER pointer
        and the second being an integer that is the required buffer size
    """

    evp_cipher = {
        'aes128': libcrypto.EVP_aes_128_cbc,
        'aes192': libcrypto.EVP_aes_192_cbc,
        'aes256': libcrypto.EVP_aes_256_cbc,
        'rc2': libcrypto.EVP_rc2_cbc,
        'rc4': libcrypto.EVP_rc4,
        'des': libcrypto.EVP_des_cbc,
        'tripledes_2key': libcrypto.EVP_des_ede_cbc,
        'tripledes_3key': libcrypto.EVP_des_ede3_cbc,
    }[cipher]()

    if cipher == 'rc4':
        buffer_size = len(data)
    else:
        block_size = {
            'aes128': 16,
            'aes192': 16,
            'aes256': 16,
            'rc2': 8,
            'des': 8,
            'tripledes_2key': 8,
            'tripledes_3key': 8,
        }[cipher]
        buffer_size = block_size * int(math.ceil(len(data) / block_size))

    return (evp_cipher, buffer_size)
