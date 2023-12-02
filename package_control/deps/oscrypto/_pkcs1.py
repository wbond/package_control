# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import sys
import hashlib
import math
import platform
import struct
import os

from . import backend
from .util import constant_compare, rand_bytes
from ._asn1 import (
    Certificate,
    int_from_bytes,
    int_to_bytes,
    PrivateKeyInfo,
    PublicKeyInfo,
)
from ._errors import pretty_message
from ._int import fill_width
from ._types import type_name, byte_cls, int_types

if sys.version_info < (3,):
    chr_cls = chr
    range = xrange  # noqa

else:
    def chr_cls(num):
        return bytes([num])


_backend = backend()


__all__ = [
    'add_pss_padding',
    'add_pkcs1v15_signature_padding',
    'raw_rsa_private_crypt',
    'raw_rsa_public_crypt',
    'remove_pkcs1v15_encryption_padding',
    'remove_pkcs1v15_signature_padding',
    'verify_pss_padding',
]


def _is_osx_107():
    """
    :return:
        A bool if the current machine is running OS X 10.7
    """

    if sys.platform != 'darwin':
        return False
    version = platform.mac_ver()[0]
    return tuple(map(int, version.split('.')))[0:2] == (10, 7)


def add_pss_padding(hash_algorithm, salt_length, key_length, message):
    """
    Pads a byte string using the EMSA-PSS-Encode operation described in PKCS#1
    v2.2.

    :param hash_algorithm:
        The string name of the hash algorithm to use: "sha1", "sha224",
        "sha256", "sha384", "sha512"

    :param salt_length:
        The length of the salt as an integer - typically the same as the length
        of the output from the hash_algorithm

    :param key_length:
        The length of the RSA key, in bits

    :param message:
        A byte string of the message to pad

    :return:
        The encoded (passed) message
    """

    if _backend != 'winlegacy' and sys.platform != 'darwin':
        raise SystemError(pretty_message(
            '''
            Pure-python RSA PSS signature padding addition code is only for
            Windows XP/2003 and OS X
            '''
        ))

    if not isinstance(message, byte_cls):
        raise TypeError(pretty_message(
            '''
            message must be a byte string, not %s
            ''',
            type_name(message)
        ))

    if not isinstance(salt_length, int_types):
        raise TypeError(pretty_message(
            '''
            salt_length must be an integer, not %s
            ''',
            type_name(salt_length)
        ))

    if salt_length < 0:
        raise ValueError(pretty_message(
            '''
            salt_length must be 0 or more - is %s
            ''',
            repr(salt_length)
        ))

    if not isinstance(key_length, int_types):
        raise TypeError(pretty_message(
            '''
            key_length must be an integer, not %s
            ''',
            type_name(key_length)
        ))

    if key_length < 512:
        raise ValueError(pretty_message(
            '''
            key_length must be 512 or more - is %s
            ''',
            repr(key_length)
        ))

    if hash_algorithm not in set(['sha1', 'sha224', 'sha256', 'sha384', 'sha512']):
        raise ValueError(pretty_message(
            '''
            hash_algorithm must be one of "sha1", "sha224", "sha256", "sha384",
            "sha512", not %s
            ''',
            repr(hash_algorithm)
        ))

    hash_func = getattr(hashlib, hash_algorithm)

    # The maximal bit size of a non-negative integer is one less than the bit
    # size of the key since the first bit is used to store sign
    em_bits = key_length - 1
    em_len = int(math.ceil(em_bits / 8))

    message_digest = hash_func(message).digest()
    hash_length = len(message_digest)

    if em_len < hash_length + salt_length + 2:
        raise ValueError(pretty_message(
            '''
            Key is not long enough to use with specified hash_algorithm and
            salt_length
            '''
        ))

    if salt_length > 0:
        salt = os.urandom(salt_length)
    else:
        salt = b''

    m_prime = (b'\x00' * 8) + message_digest + salt

    m_prime_digest = hash_func(m_prime).digest()

    padding = b'\x00' * (em_len - salt_length - hash_length - 2)

    db = padding + b'\x01' + salt

    db_mask = _mgf1(hash_algorithm, m_prime_digest, em_len - hash_length - 1)

    masked_db = int_to_bytes(int_from_bytes(db) ^ int_from_bytes(db_mask))
    masked_db = fill_width(masked_db, len(db_mask))

    zero_bits = (8 * em_len) - em_bits
    left_bit_mask = ('0' * zero_bits) + ('1' * (8 - zero_bits))
    left_int_mask = int(left_bit_mask, 2)

    if left_int_mask != 255:
        masked_db = chr_cls(left_int_mask & ord(masked_db[0:1])) + masked_db[1:]

    return masked_db + m_prime_digest + b'\xBC'


def verify_pss_padding(hash_algorithm, salt_length, key_length, message, signature):
    """
    Verifies the PSS padding on an encoded message

    :param hash_algorithm:
        The string name of the hash algorithm to use: "sha1", "sha224",
        "sha256", "sha384", "sha512"

    :param salt_length:
        The length of the salt as an integer - typically the same as the length
        of the output from the hash_algorithm

    :param key_length:
        The length of the RSA key, in bits

    :param message:
        A byte string of the message to pad

    :param signature:
        The signature to verify

    :return:
        A boolean indicating if the signature is invalid
    """

    if _backend != 'winlegacy' and sys.platform != 'darwin':
        raise SystemError(pretty_message(
            '''
            Pure-python RSA PSS signature padding verification code is only for
            Windows XP/2003 and OS X
            '''
        ))

    if not isinstance(message, byte_cls):
        raise TypeError(pretty_message(
            '''
            message must be a byte string, not %s
            ''',
            type_name(message)
        ))

    if not isinstance(signature, byte_cls):
        raise TypeError(pretty_message(
            '''
            signature must be a byte string, not %s
            ''',
            type_name(signature)
        ))

    if not isinstance(salt_length, int_types):
        raise TypeError(pretty_message(
            '''
            salt_length must be an integer, not %s
            ''',
            type_name(salt_length)
        ))

    if salt_length < 0:
        raise ValueError(pretty_message(
            '''
            salt_length must be 0 or more - is %s
            ''',
            repr(salt_length)
        ))

    if hash_algorithm not in set(['sha1', 'sha224', 'sha256', 'sha384', 'sha512']):
        raise ValueError(pretty_message(
            '''
            hash_algorithm must be one of "sha1", "sha224", "sha256", "sha384",
            "sha512", not %s
            ''',
            repr(hash_algorithm)
        ))

    hash_func = getattr(hashlib, hash_algorithm)

    em_bits = key_length - 1
    em_len = int(math.ceil(em_bits / 8))

    message_digest = hash_func(message).digest()
    hash_length = len(message_digest)

    if em_len < hash_length + salt_length + 2:
        return False

    if signature[-1:] != b'\xBC':
        return False

    zero_bits = (8 * em_len) - em_bits

    masked_db_length = em_len - hash_length - 1
    masked_db = signature[0:masked_db_length]

    first_byte = ord(masked_db[0:1])
    bits_that_should_be_zero = first_byte >> (8 - zero_bits)
    if bits_that_should_be_zero != 0:
        return False

    m_prime_digest = signature[masked_db_length:masked_db_length + hash_length]

    db_mask = _mgf1(hash_algorithm, m_prime_digest, em_len - hash_length - 1)

    left_bit_mask = ('0' * zero_bits) + ('1' * (8 - zero_bits))
    left_int_mask = int(left_bit_mask, 2)

    if left_int_mask != 255:
        db_mask = chr_cls(left_int_mask & ord(db_mask[0:1])) + db_mask[1:]

    db = int_to_bytes(int_from_bytes(masked_db) ^ int_from_bytes(db_mask))
    if len(db) < len(masked_db):
        db = (b'\x00' * (len(masked_db) - len(db))) + db

    zero_length = em_len - hash_length - salt_length - 2
    zero_string = b'\x00' * zero_length
    if not constant_compare(db[0:zero_length], zero_string):
        return False

    if db[zero_length:zero_length + 1] != b'\x01':
        return False

    salt = db[0 - salt_length:]

    m_prime = (b'\x00' * 8) + message_digest + salt

    h_prime = hash_func(m_prime).digest()

    return constant_compare(m_prime_digest, h_prime)


def _mgf1(hash_algorithm, seed, mask_length):
    """
    The PKCS#1 MGF1 mask generation algorithm

    :param hash_algorithm:
        The string name of the hash algorithm to use: "sha1", "sha224",
        "sha256", "sha384", "sha512"

    :param seed:
        A byte string to use as the seed for the mask

    :param mask_length:
        The desired mask length, as an integer

    :return:
        A byte string of the mask
    """

    if not isinstance(seed, byte_cls):
        raise TypeError(pretty_message(
            '''
            seed must be a byte string, not %s
            ''',
            type_name(seed)
        ))

    if not isinstance(mask_length, int_types):
        raise TypeError(pretty_message(
            '''
            mask_length must be an integer, not %s
            ''',
            type_name(mask_length)
        ))

    if mask_length < 1:
        raise ValueError(pretty_message(
            '''
            mask_length must be greater than 0 - is %s
            ''',
            repr(mask_length)
        ))

    if hash_algorithm not in set(['sha1', 'sha224', 'sha256', 'sha384', 'sha512']):
        raise ValueError(pretty_message(
            '''
            hash_algorithm must be one of "sha1", "sha224", "sha256", "sha384",
            "sha512", not %s
            ''',
            repr(hash_algorithm)
        ))

    output = b''

    hash_length = {
        'sha1': 20,
        'sha224': 28,
        'sha256': 32,
        'sha384': 48,
        'sha512': 64
    }[hash_algorithm]

    iterations = int(math.ceil(mask_length / hash_length))

    pack = struct.Struct(b'>I').pack
    hash_func = getattr(hashlib, hash_algorithm)

    for counter in range(0, iterations):
        b = pack(counter)
        output += hash_func(seed + b).digest()

    return output[0:mask_length]


def add_pkcs1v15_signature_padding(key_length, data):
    """
    Adds PKCS#1 v1.5 padding to a message to be signed

    :param key_length:
        An integer of the number of bytes in the key

    :param data:
        A byte string to pad

    :return:
        The padded data as a byte string
    """

    if _backend != 'winlegacy':
        raise SystemError(pretty_message(
            '''
            Pure-python RSA PKCSv1.5 signature padding addition code is only
            for Windows XP/2003
            '''
        ))

    return _add_pkcs1v15_padding(key_length, data, 'signing')


def remove_pkcs1v15_signature_padding(key_length, data):
    """
    Removes PKCS#1 v1.5 padding from a signed message using constant time
    operations

    :param key_length:
        An integer of the number of bytes in the key

    :param data:
        A byte string to unpad

    :return:
        The unpadded data as a byte string
    """

    if _backend != 'winlegacy':
        raise SystemError(pretty_message(
            '''
            Pure-python RSA PKCSv1.5 signature padding removal code is only for
            Windows XP/2003
            '''
        ))

    return _remove_pkcs1v15_padding(key_length, data, 'verifying')


def remove_pkcs1v15_encryption_padding(key_length, data):
    """
    Removes PKCS#1 v1.5 padding from a decrypted message using constant time
    operations

    :param key_length:
        An integer of the number of bytes in the key

    :param data:
        A byte string to unpad

    :return:
        The unpadded data as a byte string
    """

    if not _is_osx_107():
        raise SystemError(pretty_message(
            '''
            Pure-python RSA PKCSv1.5 encryption padding removal code is only
            for OS X 10.7
            '''
        ))

    return _remove_pkcs1v15_padding(key_length, data, 'decrypting')


def _add_pkcs1v15_padding(key_length, data, operation):
    """
    Adds PKCS#1 v1.5 padding to a message

    :param key_length:
        An integer of the number of bytes in the key

    :param data:
        A byte string to unpad

    :param operation:
        A unicode string of "encrypting" or "signing"

    :return:
        The padded data as a byte string
    """

    if operation == 'encrypting':
        second_byte = b'\x02'
    else:
        second_byte = b'\x01'

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    if not isinstance(key_length, int_types):
        raise TypeError(pretty_message(
            '''
            key_length must be an integer, not %s
            ''',
            type_name(key_length)
        ))

    if key_length < 64:
        raise ValueError(pretty_message(
            '''
            key_length must be 64 or more - is %s
            ''',
            repr(key_length)
        ))

    if len(data) > key_length - 11:
        raise ValueError(pretty_message(
            '''
            data must be between 1 and %s bytes long - is %s
            ''',
            key_length - 11,
            len(data)
        ))

    required_bytes = key_length - 3 - len(data)
    padding = b''
    while required_bytes > 0:
        temp_padding = rand_bytes(required_bytes)
        # Remove null bytes since they are markers in PKCS#1 v1.5
        temp_padding = b''.join(temp_padding.split(b'\x00'))
        padding += temp_padding
        required_bytes -= len(temp_padding)

    return b'\x00' + second_byte + padding + b'\x00' + data


def _remove_pkcs1v15_padding(key_length, data, operation):
    """
    Removes PKCS#1 v1.5 padding from a message using constant time operations

    :param key_length:
        An integer of the number of bytes in the key

    :param data:
        A byte string to unpad

    :param operation:
        A unicode string of "decrypting" or "verifying"

    :return:
        The unpadded data as a byte string
    """

    if operation == 'decrypting':
        second_byte = 2
    else:
        second_byte = 1

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    if not isinstance(key_length, int_types):
        raise TypeError(pretty_message(
            '''
            key_length must be an integer, not %s
            ''',
            type_name(key_length)
        ))

    if key_length < 64:
        raise ValueError(pretty_message(
            '''
            key_length must be 64 or more - is %s
            ''',
            repr(key_length)
        ))

    if len(data) != key_length:
        raise ValueError('Error %s' % operation)

    error = 0
    trash = 0
    padding_end = 0

    # Uses bitwise operations on an error variable and another trash variable
    # to perform constant time error checking/token scanning on the data
    for i in range(0, len(data)):
        byte = data[i:i + 1]
        byte_num = ord(byte)

        # First byte should be \x00
        if i == 0:
            error |= byte_num

        # Second byte should be \x02 for decryption, \x01 for verification
        elif i == 1:
            error |= int((byte_num | second_byte) != second_byte)

        # Bytes 3-10 should not be \x00
        elif i < 10:
            error |= int((byte_num ^ 0) == 0)

        # Byte 11 or after that is zero is end of padding
        else:
            non_zero = byte_num | 0
            if padding_end == 0:
                if non_zero:
                    trash |= i
                else:
                    padding_end |= i
            else:
                if non_zero:
                    trash |= i
                else:
                    trash |= i

    if error != 0:
        raise ValueError('Error %s' % operation)

    return data[padding_end + 1:]


def raw_rsa_private_crypt(private_key, data):
    """
    Performs a raw RSA algorithm in a byte string using a private key.
    This is a low-level primitive and is prone to disastrous results if used
    incorrectly.

    :param private_key:
        An oscrypto.asymmetric.PrivateKey object

    :param data:
        A byte string of the plaintext to be signed or ciphertext to be
        decrypted. Must be less than or equal to the length of the private key.
        In the case of signing, padding must already be applied. In the case of
        decryption, padding must be removed afterward.

    :return:
        A byte string of the transformed data
    """

    if _backend != 'winlegacy':
        raise SystemError('Pure-python RSA crypt is only for Windows XP/2003')

    if not hasattr(private_key, 'asn1') or not isinstance(private_key.asn1, PrivateKeyInfo):
        raise TypeError(pretty_message(
            '''
            private_key must be an instance of the
            oscrypto.asymmetric.PrivateKey class, not %s
            ''',
            type_name(private_key)
        ))

    algo = private_key.asn1['private_key_algorithm']['algorithm'].native
    if algo != 'rsa' and algo != 'rsassa_pss':
        raise ValueError(pretty_message(
            '''
            private_key must be an RSA key, not %s
            ''',
            algo.upper()
        ))

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    rsa_private_key = private_key.asn1['private_key'].parsed
    transformed_int = pow(
        int_from_bytes(data),
        rsa_private_key['private_exponent'].native,
        rsa_private_key['modulus'].native
    )
    return int_to_bytes(transformed_int, width=private_key.asn1.byte_size)


def raw_rsa_public_crypt(certificate_or_public_key, data):
    """
    Performs a raw RSA algorithm in a byte string using a certificate or
    public key. This is a low-level primitive and is prone to disastrous results
    if used incorrectly.

    :param certificate_or_public_key:
        An oscrypto.asymmetric.PublicKey or oscrypto.asymmetric.Certificate
        object

    :param data:
        A byte string of the signature when verifying, or padded plaintext when
        encrypting. Must be less than or equal to the length of the public key.
        When verifying, padding will need to be removed afterwards. When
        encrypting, padding must be applied before.

    :return:
        A byte string of the transformed data
    """

    if _backend != 'winlegacy':
        raise SystemError('Pure-python RSA crypt is only for Windows XP/2003')

    has_asn1 = hasattr(certificate_or_public_key, 'asn1')
    valid_types = (PublicKeyInfo, Certificate)
    if not has_asn1 or not isinstance(certificate_or_public_key.asn1, valid_types):
        raise TypeError(pretty_message(
            '''
            certificate_or_public_key must be an instance of the
            oscrypto.asymmetric.PublicKey or oscrypto.asymmetric.Certificate
            classes, not %s
            ''',
            type_name(certificate_or_public_key)
        ))

    algo = certificate_or_public_key.asn1['algorithm']['algorithm'].native
    if algo != 'rsa' and algo != 'rsassa_pss':
        raise ValueError(pretty_message(
            '''
            certificate_or_public_key must be an RSA key, not %s
            ''',
            algo.upper()
        ))

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    rsa_public_key = certificate_or_public_key.asn1['public_key'].parsed
    transformed_int = pow(
        int_from_bytes(data),
        rsa_public_key['public_exponent'].native,
        rsa_public_key['modulus'].native
    )
    return int_to_bytes(
        transformed_int,
        width=certificate_or_public_key.asn1.byte_size
    )
