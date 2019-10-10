# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import hashlib
import binascii

from . import backend
from ._asn1 import (
    armor,
    Certificate as Asn1Certificate,
    DHParameters,
    EncryptedPrivateKeyInfo,
    Null,
    OrderedDict,
    Pbkdf2Salt,
    PrivateKeyInfo,
    PublicKeyInfo,
)
from ._asymmetric import _unwrap_private_key_info
from ._errors import pretty_message
from ._types import type_name, str_cls
from .kdf import pbkdf2, pbkdf2_iteration_calculator
from .symmetric import aes_cbc_pkcs7_encrypt
from .util import rand_bytes


_backend = backend()


if _backend == 'mac':
    from ._mac.asymmetric import (
        Certificate,
        dsa_sign,
        dsa_verify,
        ecdsa_sign,
        ecdsa_verify,
        generate_pair,
        generate_dh_parameters,
        load_certificate,
        load_pkcs12,
        load_private_key,
        load_public_key,
        PrivateKey,
        PublicKey,
        rsa_pkcs1v15_sign,
        rsa_pkcs1v15_verify,
        rsa_pss_sign,
        rsa_pss_verify,
        rsa_pkcs1v15_encrypt,
        rsa_pkcs1v15_decrypt,
        rsa_oaep_encrypt,
        rsa_oaep_decrypt,
    )

elif _backend == 'win' or _backend == 'winlegacy':
    from ._win.asymmetric import (
        Certificate,
        dsa_sign,
        dsa_verify,
        ecdsa_sign,
        ecdsa_verify,
        generate_pair,
        generate_dh_parameters,
        load_certificate,
        load_pkcs12,
        load_private_key,
        load_public_key,
        PrivateKey,
        PublicKey,
        rsa_pkcs1v15_sign,
        rsa_pkcs1v15_verify,
        rsa_pss_sign,
        rsa_pss_verify,
        rsa_pkcs1v15_encrypt,
        rsa_pkcs1v15_decrypt,
        rsa_oaep_encrypt,
        rsa_oaep_decrypt,
    )

else:
    from ._openssl.asymmetric import (
        Certificate,
        dsa_sign,
        dsa_verify,
        ecdsa_sign,
        ecdsa_verify,
        generate_pair,
        generate_dh_parameters,
        load_certificate,
        load_pkcs12,
        load_private_key,
        load_public_key,
        PrivateKey,
        PublicKey,
        rsa_pkcs1v15_sign,
        rsa_pkcs1v15_verify,
        rsa_pss_sign,
        rsa_pss_verify,
        rsa_pkcs1v15_encrypt,
        rsa_pkcs1v15_decrypt,
        rsa_oaep_encrypt,
        rsa_oaep_decrypt,
    )


__all__ = [
    'Certificate',
    'dsa_sign',
    'dsa_verify',
    'dump_certificate',
    'dump_dh_parameters',
    'dump_openssl_private_key',
    'dump_private_key',
    'dump_public_key',
    'ecdsa_sign',
    'ecdsa_verify',
    'generate_pair',
    'generate_dh_parameters',
    'load_certificate',
    'load_pkcs12',
    'load_private_key',
    'load_public_key',
    'PrivateKey',
    'PublicKey',
    'rsa_oaep_decrypt',
    'rsa_oaep_encrypt',
    'rsa_pkcs1v15_decrypt',
    'rsa_pkcs1v15_encrypt',
    'rsa_pkcs1v15_sign',
    'rsa_pkcs1v15_verify',
    'rsa_pss_sign',
    'rsa_pss_verify',
]


def dump_dh_parameters(dh_parameters, encoding='pem'):
    """
    Serializes an asn1crypto.algos.DHParameters object into a byte string

    :param dh_parameters:
        An asn1crypto.algos.DHParameters object

    :param encoding:
        A unicode string of "pem" or "der"

    :return:
        A byte string of the encoded DH parameters
    """

    if encoding not in set(['pem', 'der']):
        raise ValueError(pretty_message(
            '''
            encoding must be one of "pem", "der", not %s
            ''',
            repr(encoding)
        ))

    if not isinstance(dh_parameters, DHParameters):
        raise TypeError(pretty_message(
            '''
            dh_parameters must be an instance of asn1crypto.algos.DHParameters,
            not %s
            ''',
            type_name(dh_parameters)
        ))

    output = dh_parameters.dump()
    if encoding == 'pem':
        output = armor('DH PARAMETERS', output)
    return output


def dump_public_key(public_key, encoding='pem'):
    """
    Serializes a public key object into a byte string

    :param public_key:
        An oscrypto.asymmetric.PublicKey or asn1crypto.keys.PublicKeyInfo object

    :param encoding:
        A unicode string of "pem" or "der"

    :return:
        A byte string of the encoded public key
    """

    if encoding not in set(['pem', 'der']):
        raise ValueError(pretty_message(
            '''
            encoding must be one of "pem", "der", not %s
            ''',
            repr(encoding)
        ))

    is_oscrypto = isinstance(public_key, PublicKey)
    if not isinstance(public_key, PublicKeyInfo) and not is_oscrypto:
        raise TypeError(pretty_message(
            '''
            public_key must be an instance of oscrypto.asymmetric.PublicKey or
            asn1crypto.keys.PublicKeyInfo, not %s
            ''',
            type_name(public_key)
        ))

    if is_oscrypto:
        public_key = public_key.asn1

    output = public_key.dump()
    if encoding == 'pem':
        output = armor('PUBLIC KEY', output)
    return output


def dump_certificate(certificate, encoding='pem'):
    """
    Serializes a certificate object into a byte string

    :param certificate:
        An oscrypto.asymmetric.Certificate or asn1crypto.x509.Certificate object

    :param encoding:
        A unicode string of "pem" or "der"

    :return:
        A byte string of the encoded certificate
    """

    if encoding not in set(['pem', 'der']):
        raise ValueError(pretty_message(
            '''
            encoding must be one of "pem", "der", not %s
            ''',
            repr(encoding)
        ))

    is_oscrypto = isinstance(certificate, Certificate)
    if not isinstance(certificate, Asn1Certificate) and not is_oscrypto:
        raise TypeError(pretty_message(
            '''
            certificate must be an instance of oscrypto.asymmetric.Certificate
            or asn1crypto.x509.Certificate, not %s
            ''',
            type_name(certificate)
        ))

    if is_oscrypto:
        certificate = certificate.asn1

    output = certificate.dump()
    if encoding == 'pem':
        output = armor('CERTIFICATE', output)
    return output


def dump_private_key(private_key, passphrase, encoding='pem', target_ms=200):
    """
    Serializes a private key object into a byte string of the PKCS#8 format

    :param private_key:
        An oscrypto.asymmetric.PrivateKey or asn1crypto.keys.PrivateKeyInfo
        object

    :param passphrase:
        A unicode string of the passphrase to encrypt the private key with.
        A passphrase of None will result in no encryption. A blank string will
        result in a ValueError to help ensure that the lack of passphrase is
        intentional.

    :param encoding:
        A unicode string of "pem" or "der"

    :param target_ms:
        Use PBKDF2 with the number of iterations that takes about this many
        milliseconds on the current machine.

    :raises:
        ValueError - when a blank string is provided for the passphrase

    :return:
        A byte string of the encoded and encrypted public key
    """

    if encoding not in set(['pem', 'der']):
        raise ValueError(pretty_message(
            '''
            encoding must be one of "pem", "der", not %s
            ''',
            repr(encoding)
        ))

    if passphrase is not None:
        if not isinstance(passphrase, str_cls):
            raise TypeError(pretty_message(
                '''
                passphrase must be a unicode string, not %s
                ''',
                type_name(passphrase)
            ))
        if passphrase == '':
            raise ValueError(pretty_message(
                '''
                passphrase may not be a blank string - pass None to disable
                encryption
                '''
            ))

    is_oscrypto = isinstance(private_key, PrivateKey)
    if not isinstance(private_key, PrivateKeyInfo) and not is_oscrypto:
        raise TypeError(pretty_message(
            '''
            private_key must be an instance of oscrypto.asymmetric.PrivateKey
            or asn1crypto.keys.PrivateKeyInfo, not %s
            ''',
            type_name(private_key)
        ))

    if is_oscrypto:
        private_key = private_key.asn1

    output = private_key.dump()

    if passphrase is not None:
        cipher = 'aes256_cbc'
        key_length = 32
        kdf_hmac = 'sha256'
        kdf_salt = rand_bytes(key_length)
        iterations = pbkdf2_iteration_calculator(kdf_hmac, key_length, target_ms=target_ms, quiet=True)
        # Need a bare minimum of 10,000 iterations for PBKDF2 as of 2015
        if iterations < 10000:
            iterations = 10000

        passphrase_bytes = passphrase.encode('utf-8')
        key = pbkdf2(kdf_hmac, passphrase_bytes, kdf_salt, iterations, key_length)
        iv, ciphertext = aes_cbc_pkcs7_encrypt(key, output, None)

        output = EncryptedPrivateKeyInfo({
            'encryption_algorithm': {
                'algorithm': 'pbes2',
                'parameters': {
                    'key_derivation_func': {
                        'algorithm': 'pbkdf2',
                        'parameters': {
                            'salt': Pbkdf2Salt(
                                name='specified',
                                value=kdf_salt
                            ),
                            'iteration_count': iterations,
                            'prf': {
                                'algorithm': kdf_hmac,
                                'parameters': Null()
                            }
                        }
                    },
                    'encryption_scheme': {
                        'algorithm': cipher,
                        'parameters': iv
                    }
                }
            },
            'encrypted_data': ciphertext
        }).dump()

    if encoding == 'pem':
        if passphrase is None:
            object_type = 'PRIVATE KEY'
        else:
            object_type = 'ENCRYPTED PRIVATE KEY'
        output = armor(object_type, output)

    return output


def dump_openssl_private_key(private_key, passphrase):
    """
    Serializes a private key object into a byte string of the PEM formats used
    by OpenSSL. The format chosen will depend on the type of private key - RSA,
    DSA or EC.

    Do not use this method unless you really must interact with a system that
    does not support PKCS#8 private keys. The encryption provided by PKCS#8 is
    far superior to the OpenSSL formats. This is due to the fact that the
    OpenSSL formats don't stretch the passphrase, making it very easy to
    brute-force.

    :param private_key:
        An oscrypto.asymmetric.PrivateKey or asn1crypto.keys.PrivateKeyInfo
        object

    :param passphrase:
        A unicode string of the passphrase to encrypt the private key with.
        A passphrase of None will result in no encryption. A blank string will
        result in a ValueError to help ensure that the lack of passphrase is
        intentional.

    :raises:
        ValueError - when a blank string is provided for the passphrase

    :return:
        A byte string of the encoded and encrypted public key
    """

    if passphrase is not None:
        if not isinstance(passphrase, str_cls):
            raise TypeError(pretty_message(
                '''
                passphrase must be a unicode string, not %s
                ''',
                type_name(passphrase)
            ))
        if passphrase == '':
            raise ValueError(pretty_message(
                '''
                passphrase may not be a blank string - pass None to disable
                encryption
                '''
            ))

    is_oscrypto = isinstance(private_key, PrivateKey)
    if not isinstance(private_key, PrivateKeyInfo) and not is_oscrypto:
        raise TypeError(pretty_message(
            '''
            private_key must be an instance of oscrypto.asymmetric.PrivateKey or
            asn1crypto.keys.PrivateKeyInfo, not %s
            ''',
            type_name(private_key)
        ))

    if is_oscrypto:
        private_key = private_key.asn1

    output = _unwrap_private_key_info(private_key).dump()

    headers = None
    if passphrase is not None:
        iv = rand_bytes(16)

        headers = OrderedDict()
        headers['Proc-Type'] = '4,ENCRYPTED'
        headers['DEK-Info'] = 'AES-128-CBC,%s' % binascii.hexlify(iv).decode('ascii')

        key_length = 16
        passphrase_bytes = passphrase.encode('utf-8')

        key = hashlib.md5(passphrase_bytes + iv[0:8]).digest()
        while key_length > len(key):
            key += hashlib.md5(key + passphrase_bytes + iv[0:8]).digest()
        key = key[0:key_length]

        iv, output = aes_cbc_pkcs7_encrypt(key, output, iv)

    if private_key.algorithm == 'ec':
        object_type = 'EC PRIVATE KEY'
    elif private_key.algorithm == 'rsa':
        object_type = 'RSA PRIVATE KEY'
    elif private_key.algorithm == 'dsa':
        object_type = 'DSA PRIVATE KEY'

    return armor(object_type, output, headers=headers)
