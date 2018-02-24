# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import hashlib
import hmac
import sys

from ..asn1crypto._elliptic_curve import (
    inverse_mod,
    SECP256R1_BASE_POINT,
    SECP384R1_BASE_POINT,
    SECP521R1_BASE_POINT,
    PrimePoint,
)
from ..asn1crypto import keys
from ..asn1crypto.algos import DSASignature
from ..asn1crypto.x509 import Certificate
from ..asn1crypto.util import int_from_bytes

from . import backend
from ._errors import pretty_message
from ._types import type_name, byte_cls
from .util import rand_bytes
from .errors import SignatureError

if sys.version_info < (3,):
    chr_cls = chr
    range = xrange  # noqa

else:
    def chr_cls(num):
        return bytes([num])


_backend = backend()


if _backend != 'winlegacy':
    # This pure-Python ECDSA code is only suitable for use on client machines,
    # and is only needed on Windows 5.x (XP/2003). For testing sake it is
    # possible to force use of it on newer versions of Windows.
    raise SystemError('Pure-python ECDSA code is only for Windows XP/2003')


__all__ = [
    'ec_generate_pair',
    'ecdsa_sign',
    'ecdsa_verify',
]


CURVE_BYTES = {
    'secp256r1': 32,
    'secp384r1': 48,
    'secp521r1': 66,
}

CURVE_EXTRA_BITS = {
    'secp256r1': 0,
    'secp384r1': 0,
    'secp521r1': 7,
}


def ec_generate_pair(curve):
    """
    Generates a EC public/private key pair

    :param curve:
        A unicode string. Valid values include "secp256r1", "secp384r1" and
        "secp521r1".

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type

    :return:
        A 2-element tuple of (asn1crypto.keys.PublicKeyInfo,
        asn1crypto.keys.PrivateKeyInfo)
    """

    if curve not in set(['secp256r1', 'secp384r1', 'secp521r1']):
        raise ValueError(pretty_message(
            '''
            curve must be one of "secp256r1", "secp384r1", "secp521r1", not %s
            ''',
            repr(curve)
        ))

    curve_num_bytes = CURVE_BYTES[curve]
    curve_base_point = {
        'secp256r1': SECP256R1_BASE_POINT,
        'secp384r1': SECP384R1_BASE_POINT,
        'secp521r1': SECP521R1_BASE_POINT,
    }[curve]

    while True:
        private_key_bytes = rand_bytes(curve_num_bytes)
        private_key_int = int_from_bytes(private_key_bytes, signed=False)

        if private_key_int > 0 and private_key_int < curve_base_point.order:
            break

    private_key_info = keys.PrivateKeyInfo({
        'version': 0,
        'private_key_algorithm': keys.PrivateKeyAlgorithm({
            'algorithm': 'ec',
            'parameters': keys.ECDomainParameters(
                name='named',
                value=curve
            )
        }),
        'private_key': keys.ECPrivateKey({
            'version': 'ecPrivkeyVer1',
            'private_key': private_key_int
        }),
    })
    private_key_info['private_key'].parsed['public_key'] = private_key_info.public_key
    public_key_info = private_key_info.public_key_info

    return (public_key_info, private_key_info)


def ecdsa_sign(private_key, data, hash_algorithm):
    """
    Generates an ECDSA signature in pure Python (thus slow)

    :param private_key:
        The PrivateKey to generate the signature with

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "sha1", "sha256", "sha384" or "sha512"

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the signature
    """

    if not hasattr(private_key, 'asn1') or not isinstance(private_key.asn1, keys.PrivateKeyInfo):
        raise TypeError(pretty_message(
            '''
            private_key must be an instance of the
            oscrypto.asymmetric.PrivateKey class, not %s
            ''',
            type_name(private_key)
        ))

    curve_name = private_key.curve
    if curve_name not in set(['secp256r1', 'secp384r1', 'secp521r1']):
        raise ValueError(pretty_message(
            '''
            private_key does not use one of the named curves secp256r1,
            secp384r1 or secp521r1
            '''
        ))

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
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

    ec_private_key = private_key.asn1['private_key'].parsed
    private_key_bytes = ec_private_key['private_key'].contents
    private_key_int = ec_private_key['private_key'].native

    curve_num_bytes = CURVE_BYTES[curve_name]
    curve_base_point = {
        'secp256r1': SECP256R1_BASE_POINT,
        'secp384r1': SECP384R1_BASE_POINT,
        'secp521r1': SECP521R1_BASE_POINT,
    }[curve_name]

    n = curve_base_point.order

    # RFC 6979 section 3.2

    # a.
    digest = hash_func(data).digest()
    hash_length = len(digest)

    h = int_from_bytes(digest, signed=False) % n

    # b.
    V = b'\x01' * hash_length

    # c.
    K = b'\x00' * hash_length

    # d.
    K = hmac.new(K, V + b'\x00' + private_key_bytes + digest, hash_func).digest()

    # e.
    V = hmac.new(K, V, hash_func).digest()

    # f.
    K = hmac.new(K, V + b'\x01' + private_key_bytes + digest, hash_func).digest()

    # g.
    V = hmac.new(K, V, hash_func).digest()

    # h.
    r = 0
    s = 0
    while True:
        # h. 1
        T = b''

        # h. 2
        while len(T) < curve_num_bytes:
            V = hmac.new(K, V, hash_func).digest()
            T += V

        # h. 3
        k = int_from_bytes(T[0:curve_num_bytes], signed=False)
        if k == 0 or k >= n:
            continue

        # Calculate the signature in the loop in case we need a new k
        r = (curve_base_point * k).x % n
        if r == 0:
            continue

        s = (inverse_mod(k, n) * (h + (private_key_int * r) % n)) % n
        if s == 0:
            continue

        break

    return DSASignature({'r': r, 's': s}).dump()


def ecdsa_verify(certificate_or_public_key, signature, data, hash_algorithm):
    """
    Verifies an ECDSA signature in pure Python (thus slow)

    :param certificate_or_public_key:
        A Certificate or PublicKey instance to verify the signature with

    :param signature:
        A byte string of the signature to verify

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha256", "sha384" or "sha512"

    :raises:
        oscrypto.errors.SignatureError - when the signature is determined to be invalid
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library
    """

    has_asn1 = hasattr(certificate_or_public_key, 'asn1')
    if not has_asn1 or not isinstance(certificate_or_public_key.asn1, (keys.PublicKeyInfo, Certificate)):
        raise TypeError(pretty_message(
            '''
            certificate_or_public_key must be an instance of the
            oscrypto.asymmetric.PublicKey or oscrypto.asymmetric.Certificate
            classes, not %s
            ''',
            type_name(certificate_or_public_key)
        ))

    curve_name = certificate_or_public_key.curve
    if curve_name not in set(['secp256r1', 'secp384r1', 'secp521r1']):
        raise ValueError(pretty_message(
            '''
            certificate_or_public_key does not use one of the named curves
            secp256r1, secp384r1 or secp521r1
            '''
        ))

    if not isinstance(signature, byte_cls):
        raise TypeError(pretty_message(
            '''
            signature must be a byte string, not %s
            ''',
            type_name(signature)
        ))

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    if hash_algorithm not in set(['sha1', 'sha224', 'sha256', 'sha384', 'sha512']):
        raise ValueError(pretty_message(
            '''
            hash_algorithm must be one of "sha1", "sha224", "sha256", "sha384",
            "sha512", not %s
            ''',
            repr(hash_algorithm)
        ))

    asn1 = certificate_or_public_key.asn1
    if isinstance(asn1, Certificate):
        asn1 = asn1.public_key

    curve_base_point = {
        'secp256r1': SECP256R1_BASE_POINT,
        'secp384r1': SECP384R1_BASE_POINT,
        'secp521r1': SECP521R1_BASE_POINT,
    }[curve_name]

    x, y = asn1['public_key'].to_coords()
    n = curve_base_point.order

    # Validates that the point is valid
    public_key_point = PrimePoint(curve_base_point.curve, x, y, n)

    try:
        signature = DSASignature.load(signature)
        r = signature['r'].native
        s = signature['s'].native
    except (ValueError):
        raise SignatureError('Signature is invalid')

    invalid = 0

    # Check r is valid
    invalid |= r < 1
    invalid |= r >= n

    # Check s is valid
    invalid |= s < 1
    invalid |= s >= n

    if invalid:
        raise SignatureError('Signature is invalid')

    hash_func = getattr(hashlib, hash_algorithm)

    digest = hash_func(data).digest()

    z = int_from_bytes(digest, signed=False) % n
    w = inverse_mod(s, n)
    u1 = (z * w) % n
    u2 = (r * w) % n
    hash_point = (curve_base_point * u1) + (public_key_point * u2)
    if r != (hash_point.x % n):
        raise SignatureError('Signature is invalid')
