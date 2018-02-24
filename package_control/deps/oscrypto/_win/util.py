# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from .. import backend
from .._errors import pretty_message
from .._ffi import buffer_from_bytes, bytes_from_buffer
from .._pkcs12 import pkcs12_kdf
from .._types import type_name, byte_cls, int_types


__all__ = [
    'pbkdf2',
    'pkcs12_kdf',
    'rand_bytes',
]


_backend = backend()


if _backend == 'win':
    from ._cng import bcrypt, BcryptConst, handle_error, open_alg_handle, close_alg_handle

    def pbkdf2(hash_algorithm, password, salt, iterations, key_length):
        """
        PBKDF2 from PKCS#5

        :param hash_algorithm:
            The string name of the hash algorithm to use: "sha1", "sha256", "sha384", "sha512"

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

        if hash_algorithm not in set(['sha1', 'sha256', 'sha384', 'sha512']):
            raise ValueError(pretty_message(
                '''
                hash_algorithm must be one of "sha1", "sha256", "sha384", "sha512",
                not %s
                ''',
                repr(hash_algorithm)
            ))

        alg_constant = {
            'sha1': BcryptConst.BCRYPT_SHA1_ALGORITHM,
            'sha256': BcryptConst.BCRYPT_SHA256_ALGORITHM,
            'sha384': BcryptConst.BCRYPT_SHA384_ALGORITHM,
            'sha512': BcryptConst.BCRYPT_SHA512_ALGORITHM
        }[hash_algorithm]

        alg_handle = None

        try:
            alg_handle = open_alg_handle(alg_constant, BcryptConst.BCRYPT_ALG_HANDLE_HMAC_FLAG)

            output_buffer = buffer_from_bytes(key_length)
            res = bcrypt.BCryptDeriveKeyPBKDF2(
                alg_handle,
                password,
                len(password),
                salt,
                len(salt),
                iterations,
                output_buffer,
                key_length,
                0
            )
            handle_error(res)

            return bytes_from_buffer(output_buffer)
        finally:
            if alg_handle:
                close_alg_handle(alg_handle)

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

        alg_handle = None

        try:
            alg_handle = open_alg_handle(BcryptConst.BCRYPT_RNG_ALGORITHM)
            buffer = buffer_from_bytes(length)

            res = bcrypt.BCryptGenRandom(alg_handle, buffer, length, 0)
            handle_error(res)

            return bytes_from_buffer(buffer)

        finally:
            if alg_handle:
                close_alg_handle(alg_handle)

# winlegacy backend
else:
    from .._pkcs5 import pbkdf2
    from .._rand import rand_bytes
