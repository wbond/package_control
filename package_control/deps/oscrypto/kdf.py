# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import sys
import hashlib
from datetime import datetime

from . import backend
from .util import rand_bytes
from ._types import type_name, byte_cls, int_types
from ._errors import pretty_message
from ._ffi import new, deref


_backend = backend()


if _backend == 'mac':
    from ._mac.util import pbkdf2, pkcs12_kdf
elif _backend == 'win' or _backend == 'winlegacy':
    from ._win.util import pbkdf2, pkcs12_kdf
    from ._win._kernel32 import kernel32, handle_error
else:
    from ._openssl.util import pbkdf2, pkcs12_kdf


__all__ = [
    'pbkdf1',
    'pbkdf2',
    'pbkdf2_iteration_calculator',
    'pkcs12_kdf',
]


if sys.platform == 'win32':
    def _get_start():
        number = new(kernel32, 'LARGE_INTEGER *')
        res = kernel32.QueryPerformanceCounter(number)
        handle_error(res)
        return deref(number)

    def _get_elapsed(start):
        length = _get_start() - start
        return int(length / 1000.0)

else:
    def _get_start():
        return datetime.now()

    def _get_elapsed(start):
        length = datetime.now() - start
        seconds = length.seconds + (length.days * 24 * 3600)
        milliseconds = (length.microseconds / 10 ** 3)
        return int(milliseconds + (seconds * 10 ** 3))


def pbkdf2_iteration_calculator(hash_algorithm, key_length, target_ms=100, quiet=False):
    """
    Runs pbkdf2() twice to determine the approximate number of iterations to
    use to hit a desired time per run. Use this on a production machine to
    dynamically adjust the number of iterations as high as you can.

    :param hash_algorithm:
        The string name of the hash algorithm to use: "md5", "sha1", "sha224",
        "sha256", "sha384", "sha512"

    :param key_length:
        The length of the desired key in bytes

    :param target_ms:
        The number of milliseconds the derivation should take

    :param quiet:
        If no output should be printed as attempts are made

    :return:
        An integer number of iterations of PBKDF2 using the specified hash
        that will take at least target_ms
    """

    if hash_algorithm not in set(['sha1', 'sha224', 'sha256', 'sha384', 'sha512']):
        raise ValueError(pretty_message(
            '''
            hash_algorithm must be one of "sha1", "sha224", "sha256", "sha384",
            "sha512", not %s
            ''',
            repr(hash_algorithm)
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

    if not isinstance(target_ms, int_types):
        raise TypeError(pretty_message(
            '''
            target_ms must be an integer, not %s
            ''',
            type_name(target_ms)
        ))

    if target_ms < 1:
        raise ValueError(pretty_message(
            '''
            target_ms must be greater than 0 - is %s
            ''',
            repr(target_ms)
        ))

    if pbkdf2.pure_python:
        raise OSError(pretty_message(
            '''
            Only a very slow, pure-python version of PBKDF2 is available,
            making this function useless
            '''
        ))

    iterations = 10000
    password = 'this is a test'.encode('utf-8')
    salt = rand_bytes(key_length)

    def _measure():
        start = _get_start()
        pbkdf2(hash_algorithm, password, salt, iterations, key_length)
        observed_ms = _get_elapsed(start)
        if not quiet:
            print('%s iterations in %sms' % (iterations, observed_ms))
        return 1.0 / target_ms * observed_ms

    # Measure the initial guess, then estimate how many iterations it would
    # take to reach 1/2 of the target ms and try it to get a good final number
    fraction = _measure()
    iterations = int(iterations / fraction / 2.0)

    fraction = _measure()
    iterations = iterations / fraction

    # < 20,000 round to 1000
    # 20,000-100,000 round to 5,000
    # > 100,000 round to 10,000
    round_factor = -3 if iterations < 100000 else -4
    result = int(round(iterations, round_factor))
    if result > 20000:
        result = (result // 5000) * 5000
    return result


def pbkdf1(hash_algorithm, password, salt, iterations, key_length):
    """
    An implementation of PBKDF1 - should only be used for interop with legacy
    systems, not new architectures

    :param hash_algorithm:
        The string name of the hash algorithm to use: "md2", "md5", "sha1"

    :param password:
        A byte string of the password to use an input to the KDF

    :param salt:
        A cryptographic random byte string

    :param iterations:
        The numbers of iterations to use when deriving the key

    :param key_length:
        The length of the desired key in bytes

    :return:
        The derived key as a byte string
    """

    if not isinstance(password, byte_cls):
        raise TypeError(pretty_message(
            '''
            password must be a byte string, not %s
            ''',
            (type_name(password))
        ))

    if not isinstance(salt, byte_cls):
        raise TypeError(pretty_message(
            '''
            salt must be a byte string, not %s
            ''',
            (type_name(salt))
        ))

    if not isinstance(iterations, int_types):
        raise TypeError(pretty_message(
            '''
            iterations must be an integer, not %s
            ''',
            (type_name(iterations))
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
            (type_name(key_length))
        ))

    if key_length < 1:
        raise ValueError(pretty_message(
            '''
            key_length must be greater than 0 - is %s
            ''',
            repr(key_length)
        ))

    if hash_algorithm not in set(['md2', 'md5', 'sha1']):
        raise ValueError(pretty_message(
            '''
            hash_algorithm must be one of "md2", "md5", "sha1", not %s
            ''',
            repr(hash_algorithm)
        ))

    if key_length > 16 and hash_algorithm in set(['md2', 'md5']):
        raise ValueError(pretty_message(
            '''
            key_length can not be longer than 16 for %s - is %s
            ''',
            (hash_algorithm, repr(key_length))
        ))

    if key_length > 20 and hash_algorithm == 'sha1':
        raise ValueError(pretty_message(
            '''
            key_length can not be longer than 20 for sha1 - is %s
            ''',
            repr(key_length)
        ))

    algo = getattr(hashlib, hash_algorithm)
    output = algo(password + salt).digest()
    for _ in range(2, iterations + 1):
        output = algo(output).digest()

    return output[:key_length]
