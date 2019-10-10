# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from .._errors import pretty_message
from .._ffi import new, null
from ._core_foundation import CoreFoundation, CFHelpers, handle_cf_error
from ._security import Security
from .util import rand_bytes
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
        OSError - when an error is returned by the OS crypto library

    :return:
        A tuple of two byte strings (iv, ciphertext)
    """

    if len(key) not in [16, 24, 32]:
        raise ValueError(pretty_message(
            '''
            key must be either 16, 24 or 32 bytes (128, 192 or 256 bits) long - is %s
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

    return (iv, _encrypt(Security.kSecAttrKeyTypeAES, key, data, iv, Security.kSecPaddingNoneKey))


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
            key must be either 16, 24 or 32 bytes (128, 192 or 256 bits) long - is %s
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

    return _decrypt(Security.kSecAttrKeyTypeAES, key, data, iv, Security.kSecPaddingNoneKey)


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
            key must be either 16, 24 or 32 bytes (128, 192 or 256 bits) long - is %s
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

    return (iv, _encrypt(Security.kSecAttrKeyTypeAES, key, data, iv, Security.kSecPaddingPKCS7Key))


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

    return _decrypt(Security.kSecAttrKeyTypeAES, key, data, iv, Security.kSecPaddingPKCS7Key)


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

    return _encrypt(Security.kSecAttrKeyTypeRC4, key, data, None, None)


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

    return _decrypt(Security.kSecAttrKeyTypeRC4, key, data, None, None)


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

    return (iv, _encrypt(Security.kSecAttrKeyTypeRC2, key, data, iv, Security.kSecPaddingPKCS5Key))


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

    return _decrypt(Security.kSecAttrKeyTypeRC2, key, data, iv, Security.kSecPaddingPKCS5Key)


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

    # Expand 2-key to actual 24 byte byte string used by cipher
    if len(key) == 16:
        key = key + key[0:8]

    return (iv, _encrypt(Security.kSecAttrKeyType3DES, key, data, iv, Security.kSecPaddingPKCS5Key))


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

    # Expand 2-key to actual 24 byte byte string used by cipher
    if len(key) == 16:
        key = key + key[0:8]

    return _decrypt(Security.kSecAttrKeyType3DES, key, data, iv, Security.kSecPaddingPKCS5Key)


def des_cbc_pkcs5_encrypt(key, data, iv):
    """
    Encrypts plaintext using DES with a 56 bit key

    :param key:
        The encryption key - a byte string 8 bytes long (includes error correction bits)

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

    return (iv, _encrypt(Security.kSecAttrKeyTypeDES, key, data, iv, Security.kSecPaddingPKCS5Key))


def des_cbc_pkcs5_decrypt(key, data, iv):
    """
    Decrypts DES ciphertext using a 56 bit key

    :param key:
        The encryption key - a byte string 8 bytes long (includes error correction bits)

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

    return _decrypt(Security.kSecAttrKeyTypeDES, key, data, iv, Security.kSecPaddingPKCS5Key)


def _encrypt(cipher, key, data, iv, padding):
    """
    Encrypts plaintext

    :param cipher:
        A kSecAttrKeyType* value that specifies the cipher to use

    :param key:
        The encryption key - a byte string 5-16 bytes long

    :param data:
        The plaintext - a byte string

    :param iv:
        The initialization vector - a byte string - unused for RC4

    :param padding:
        The padding mode to use, specified as a kSecPadding*Key value - unused for RC4

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

    if cipher != Security.kSecAttrKeyTypeRC4 and not isinstance(iv, byte_cls):
        raise TypeError(pretty_message(
            '''
            iv must be a byte string, not %s
            ''',
            type_name(iv)
        ))

    if cipher != Security.kSecAttrKeyTypeRC4 and not padding:
        raise ValueError('padding must be specified')

    cf_dict = None
    cf_key = None
    cf_data = None
    cf_iv = None
    sec_key = None
    sec_transform = None

    try:
        cf_dict = CFHelpers.cf_dictionary_from_pairs([(Security.kSecAttrKeyType, cipher)])
        cf_key = CFHelpers.cf_data_from_bytes(key)
        cf_data = CFHelpers.cf_data_from_bytes(data)

        error_pointer = new(CoreFoundation, 'CFErrorRef *')
        sec_key = Security.SecKeyCreateFromData(cf_dict, cf_key, error_pointer)
        handle_cf_error(error_pointer)

        sec_transform = Security.SecEncryptTransformCreate(sec_key, error_pointer)
        handle_cf_error(error_pointer)

        if cipher != Security.kSecAttrKeyTypeRC4:
            Security.SecTransformSetAttribute(sec_transform, Security.kSecModeCBCKey, null(), error_pointer)
            handle_cf_error(error_pointer)

            Security.SecTransformSetAttribute(sec_transform, Security.kSecPaddingKey, padding, error_pointer)
            handle_cf_error(error_pointer)

            cf_iv = CFHelpers.cf_data_from_bytes(iv)
            Security.SecTransformSetAttribute(sec_transform, Security.kSecIVKey, cf_iv, error_pointer)
            handle_cf_error(error_pointer)

        Security.SecTransformSetAttribute(
            sec_transform,
            Security.kSecTransformInputAttributeName,
            cf_data,
            error_pointer
        )
        handle_cf_error(error_pointer)

        ciphertext = Security.SecTransformExecute(sec_transform, error_pointer)
        handle_cf_error(error_pointer)

        return CFHelpers.cf_data_to_bytes(ciphertext)

    finally:
        if cf_dict:
            CoreFoundation.CFRelease(cf_dict)
        if cf_key:
            CoreFoundation.CFRelease(cf_key)
        if cf_data:
            CoreFoundation.CFRelease(cf_data)
        if cf_iv:
            CoreFoundation.CFRelease(cf_iv)
        if sec_key:
            CoreFoundation.CFRelease(sec_key)
        if sec_transform:
            CoreFoundation.CFRelease(sec_transform)


def _decrypt(cipher, key, data, iv, padding):
    """
    Decrypts AES/RC4/RC2/3DES/DES ciphertext

    :param cipher:
        A kSecAttrKeyType* value that specifies the cipher to use

    :param key:
        The encryption key - a byte string 5-16 bytes long

    :param data:
        The ciphertext - a byte string

    :param iv:
        The initialization vector - a byte string - unused for RC4

    :param padding:
        The padding mode to use, specified as a kSecPadding*Key value - unused for RC4

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

    if cipher != Security.kSecAttrKeyTypeRC4 and not isinstance(iv, byte_cls):
        raise TypeError(pretty_message(
            '''
            iv must be a byte string, not %s
            ''',
            type_name(iv)
        ))

    if cipher != Security.kSecAttrKeyTypeRC4 and not padding:
        raise ValueError('padding must be specified')

    cf_dict = None
    cf_key = None
    cf_data = None
    cf_iv = None
    sec_key = None
    sec_transform = None

    try:
        cf_dict = CFHelpers.cf_dictionary_from_pairs([(Security.kSecAttrKeyType, cipher)])
        cf_key = CFHelpers.cf_data_from_bytes(key)
        cf_data = CFHelpers.cf_data_from_bytes(data)

        error_pointer = new(CoreFoundation, 'CFErrorRef *')
        sec_key = Security.SecKeyCreateFromData(cf_dict, cf_key, error_pointer)
        handle_cf_error(error_pointer)

        sec_transform = Security.SecDecryptTransformCreate(sec_key, error_pointer)
        handle_cf_error(error_pointer)

        if cipher != Security.kSecAttrKeyTypeRC4:
            Security.SecTransformSetAttribute(sec_transform, Security.kSecModeCBCKey, null(), error_pointer)
            handle_cf_error(error_pointer)

            Security.SecTransformSetAttribute(sec_transform, Security.kSecPaddingKey, padding, error_pointer)
            handle_cf_error(error_pointer)

            cf_iv = CFHelpers.cf_data_from_bytes(iv)
            Security.SecTransformSetAttribute(sec_transform, Security.kSecIVKey, cf_iv, error_pointer)
            handle_cf_error(error_pointer)

        Security.SecTransformSetAttribute(
            sec_transform,
            Security.kSecTransformInputAttributeName,
            cf_data,
            error_pointer
        )
        handle_cf_error(error_pointer)

        plaintext = Security.SecTransformExecute(sec_transform, error_pointer)
        handle_cf_error(error_pointer)

        return CFHelpers.cf_data_to_bytes(plaintext)

    finally:
        if cf_dict:
            CoreFoundation.CFRelease(cf_dict)
        if cf_key:
            CoreFoundation.CFRelease(cf_key)
        if cf_data:
            CoreFoundation.CFRelease(cf_data)
        if cf_iv:
            CoreFoundation.CFRelease(cf_iv)
        if sec_key:
            CoreFoundation.CFRelease(sec_key)
        if sec_transform:
            CoreFoundation.CFRelease(sec_transform)
