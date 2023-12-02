# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import sys
import hashlib
import math

from ._asn1 import int_from_bytes, int_to_bytes
from ._errors import pretty_message
from ._types import type_name, byte_cls, int_types


if sys.version_info < (3,):
    chr_cls = chr

else:
    def chr_cls(num):
        return bytes([num])


__all__ = [
    'pkcs12_kdf',
]


def pkcs12_kdf(hash_algorithm, password, salt, iterations, key_length, id_):
    """
    KDF from RFC7292 appendix b.2 - https://tools.ietf.org/html/rfc7292#page-19

    :param hash_algorithm:
        The string name of the hash algorithm to use: "md5", "sha1", "sha224",
        "sha256", "sha384", "sha512"

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

    algo = getattr(hashlib, hash_algorithm)

    # u and v values are bytes (not bits as in the RFC)
    u = {
        'md5': 16,
        'sha1': 20,
        'sha224': 28,
        'sha256': 32,
        'sha384': 48,
        'sha512': 64
    }[hash_algorithm]

    if hash_algorithm in ['sha384', 'sha512']:
        v = 128
    else:
        v = 64

    # Step 1
    d = chr_cls(id_) * v

    # Step 2
    s = b''
    if salt != b'':
        s_len = v * int(math.ceil(float(len(salt)) / v))
        while len(s) < s_len:
            s += salt
        s = s[0:s_len]

    # Step 3
    p = b''
    if utf16_password != b'':
        p_len = v * int(math.ceil(float(len(utf16_password)) / v))
        while len(p) < p_len:
            p += utf16_password
        p = p[0:p_len]

    # Step 4
    i = s + p

    # Step 5
    c = int(math.ceil(float(key_length) / u))

    a = b'\x00' * (c * u)

    for num in range(1, c + 1):
        # Step 6A
        a2 = algo(d + i).digest()
        for _ in range(2, iterations + 1):
            a2 = algo(a2).digest()

        if num < c:
            # Step 6B
            b = b''
            while len(b) < v:
                b += a2

            b = int_from_bytes(b[0:v]) + 1

            # Step 6C
            for num2 in range(0, len(i) // v):
                start = num2 * v
                end = (num2 + 1) * v
                i_num2 = i[start:end]

                i_num2 = int_to_bytes(int_from_bytes(i_num2) + b)

                # Ensure the new slice is the right size
                i_num2_l = len(i_num2)
                if i_num2_l > v:
                    i_num2 = i_num2[i_num2_l - v:]

                i = i[0:start] + i_num2 + i[end:]

        # Step 7 (one piece at a time)
        begin = (num - 1) * u
        to_copy = min(key_length, u)
        a = a[0:begin] + a2[0:to_copy] + a[begin + to_copy:]

    return a[0:key_length]
