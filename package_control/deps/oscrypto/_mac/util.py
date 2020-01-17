# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import os

from .._errors import pretty_message
from .._ffi import buffer_from_bytes, bytes_from_buffer, errno, byte_string_from_buffer
from .._types import type_name, str_cls, byte_cls, int_types
from ..errors import LibraryNotFoundError
from ._common_crypto import CommonCrypto, CommonCryptoConst
from ._security import Security


__all__ = [
    'pbkdf2',
    'pkcs12_kdf',
    'rand_bytes',
]


_encoding = 'utf-8'
_fallback_encodings = ['utf-8', 'cp1252']


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


def _extract_error():
    """
    Extracts the last OS error message into a python unicode string

    :return:
        A unicode string error message
    """

    error_num = errno()

    try:
        error_string = os.strerror(error_num)
    except (ValueError):
        return str_cls(error_num)

    if isinstance(error_string, str_cls):
        return error_string

    return _try_decode(error_string)


def pbkdf2(hash_algorithm, password, salt, iterations, key_length):
    """
    PBKDF2 from PKCS#5

    :param hash_algorithm:
        The string name of the hash algorithm to use: "sha1", "sha224", "sha256", "sha384", "sha512"

    :param password:
        A byte string of the password to use an input to the KDF

    :param salt:
        A cryptographic random byte string

    :param iterations:
        The numbers of iterations to use when deriving the key

    :param key_length:
        The length of the desired key in bytes

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        The derived key as a byte string
    """

    if not isinstance(password, byte_cls):
        raise TypeError(pretty_message(
            '''
            password must be a byte string, not %s
            ''',
            type_name(password)
        ))

    if not isinstance(salt, byte_cls):
        raise TypeError(pretty_message(
            '''
            salt must be a byte string, not %s
            ''',
            type_name(salt)
        ))

    if not isinstance(iterations, int_types):
        raise TypeError(pretty_message(
            '''
            iterations must be an integer, not %s
            ''',
            type_name(iterations)
        ))

    if iterations < 1:
        raise ValueError('iterations must be greater than 0')

    if not isinstance(key_length, int_types):
        raise TypeError(pretty_message(
            '''
            key_length must be an integer, not %s
            ''',
            type_name(key_length)
        ))

    if key_length < 1:
        raise ValueError('key_length must be greater than 0')

    if hash_algorithm not in set(['sha1', 'sha224', 'sha256', 'sha384', 'sha512']):
        raise ValueError(pretty_message(
            '''
            hash_algorithm must be one of "sha1", "sha224", "sha256", "sha384",
            "sha512", not %s
            ''',
            repr(hash_algorithm)
        ))

    algo = {
        'sha1': CommonCryptoConst.kCCPRFHmacAlgSHA1,
        'sha224': CommonCryptoConst.kCCPRFHmacAlgSHA224,
        'sha256': CommonCryptoConst.kCCPRFHmacAlgSHA256,
        'sha384': CommonCryptoConst.kCCPRFHmacAlgSHA384,
        'sha512': CommonCryptoConst.kCCPRFHmacAlgSHA512
    }[hash_algorithm]

    output_buffer = buffer_from_bytes(key_length)
    result = CommonCrypto.CCKeyDerivationPBKDF(
        CommonCryptoConst.kCCPBKDF2,
        password,
        len(password),
        salt,
        len(salt),
        algo,
        iterations,
        output_buffer,
        key_length
    )
    if result != 0:
        raise OSError(_extract_error())

    return bytes_from_buffer(output_buffer)


pbkdf2.pure_python = False


def rand_bytes(length):
    """
    Returns a number of random bytes suitable for cryptographic purposes

    :param length:
        The desired number of bytes

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string
    """

    if not isinstance(length, int_types):
        raise TypeError(pretty_message(
            '''
            length must be an integer, not %s
            ''',
            type_name(length)
        ))

    if length < 1:
        raise ValueError('length must be greater than 0')

    if length > 1024:
        raise ValueError('length must not be greater than 1024')

    buffer = buffer_from_bytes(length)
    result = Security.SecRandomCopyBytes(Security.kSecRandomDefault, length, buffer)
    if result != 0:
        raise OSError(_extract_error())

    return bytes_from_buffer(buffer)


# If in a future version of OS X they remove OpenSSL, this try/except block
# will fall back to the pure Python implementation, which is just slower
try:
    from .._openssl._libcrypto import libcrypto

    def _extract_openssl_error():
        """
        Extracts the last OpenSSL error message into a python unicode string

        :return:
            A unicode string error message
        """

        error_num = libcrypto.ERR_get_error()
        buffer = buffer_from_bytes(120)
        libcrypto.ERR_error_string(error_num, buffer)

        # Since we are dealing with a string, it is NULL terminated
        error_string = byte_string_from_buffer(buffer)

        return _try_decode(error_string)

    def pkcs12_kdf(hash_algorithm, password, salt, iterations, key_length, id_):
        """
        KDF from RFC7292 appendix B.2 - https://tools.ietf.org/html/rfc7292#page-19

        :param hash_algorithm:
            The string name of the hash algorithm to use: "md5", "sha1", "sha224", "sha256", "sha384", "sha512"

        :param password:
            A byte string of the password to use an input to the KDF

        :param salt:
            A cryptographic random byte string

        :param iterations:
            The numbers of iterations to use when deriving the key

        :param key_length:
            The length of the desired key in bytes

        :param id_:
            The ID of the usage - 1 for key, 2 for iv, 3 for mac

        :raises:
            ValueError - when any of the parameters contain an invalid value
            TypeError - when any of the parameters are of the wrong type
            OSError - when an error is returned by the OS crypto library

        :return:
            The derived key as a byte string
        """

        if not isinstance(password, byte_cls):
            raise TypeError(pretty_message(
                '''
                password must be a byte string, not %s
                ''',
                type_name(password)
            ))

        if not isinstance(salt, byte_cls):
            raise TypeError(pretty_message(
                '''
                salt must be a byte string, not %s
                ''',
                type_name(salt)
            ))

        if not isinstance(iterations, int_types):
            raise TypeError(pretty_message(
                '''
                iterations must be an integer, not %s
                ''',
                type_name(iterations)
            ))

        if iterations < 1:
            raise ValueError(pretty_message(
                '''
                iterations must be greater than 0 - is %s
                ''',
                repr(iterations)
            ))

        if not isinstance(key_length, int_types):
            raise TypeError(pretty_message(
                '''
                key_length must be an integer, not %s
                ''',
                type_name(key_length)
            ))

        if key_length < 1:
            raise ValueError(pretty_message(
                '''
                key_length must be greater than 0 - is %s
                ''',
                repr(key_length)
            ))

        if hash_algorithm not in set(['md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512']):
            raise ValueError(pretty_message(
                '''
                hash_algorithm must be one of "md5", "sha1", "sha224", "sha256",
                "sha384", "sha512", not %s
                ''',
                repr(hash_algorithm)
            ))

        if id_ not in set([1, 2, 3]):
            raise ValueError(pretty_message(
                '''
                id_ must be one of 1, 2, 3, not %s
                ''',
                repr(id_)
            ))

        utf16_password = password.decode('utf-8').encode('utf-16be') + b'\x00\x00'

        digest_type = {
            'md5': libcrypto.EVP_md5,
            'sha1': libcrypto.EVP_sha1,
            'sha224': libcrypto.EVP_sha224,
            'sha256': libcrypto.EVP_sha256,
            'sha384': libcrypto.EVP_sha384,
            'sha512': libcrypto.EVP_sha512,
        }[hash_algorithm]()

        output_buffer = buffer_from_bytes(key_length)
        result = libcrypto.PKCS12_key_gen_uni(
            utf16_password,
            len(utf16_password),
            salt,
            len(salt),
            id_,
            iterations,
            key_length,
            output_buffer,
            digest_type
        )
        if result != 1:
            raise OSError(_extract_openssl_error())

        return bytes_from_buffer(output_buffer)

except (LibraryNotFoundError):

    from .._pkcs12 import pkcs12_kdf
