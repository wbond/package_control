# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import hashlib
import hmac
import re
import binascii

from ..asn1crypto import core, pkcs12, cms, keys, x509, pem

from .kdf import pbkdf1, pbkdf2, pkcs12_kdf
from .symmetric import (
    aes_cbc_pkcs7_decrypt,
    des_cbc_pkcs5_decrypt,
    rc2_cbc_pkcs5_decrypt,
    rc4_decrypt,
    tripledes_cbc_pkcs5_decrypt,
)
from .util import constant_compare
from ._errors import pretty_message
from ._types import byte_cls, type_name


__all__ = [
    'parse_certificate',
    'parse_pkcs12',
    'parse_private',
    'parse_public',
]


crypto_funcs = {
    'rc2': rc2_cbc_pkcs5_decrypt,
    'rc4': rc4_decrypt,
    'des': des_cbc_pkcs5_decrypt,
    'tripledes': tripledes_cbc_pkcs5_decrypt,
    'aes': aes_cbc_pkcs7_decrypt,
}


def parse_public(data):
    """
    Loads a public key from a DER or PEM-formatted file. Supports RSA, DSA and
    EC public keys. For RSA keys, both the old RSAPublicKey and
    SubjectPublicKeyInfo structures are supported. Also allows extracting a
    public key from an X.509 certificate.

    :param data:
        A byte string to load the public key from

    :raises:
        ValueError - when the data does not appear to contain a public key

    :return:
        An asn1crypto.keys.PublicKeyInfo object
    """

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    key_type = None

    # Appears to be PEM formatted
    if data[0:5] == b'-----':
        key_type, algo, data = _unarmor_pem(data)

        if key_type == 'private key':
            raise ValueError(pretty_message(
                '''
                The data specified does not appear to be a public key or
                certificate, but rather a private key
                '''
            ))

        # When a public key returning from _unarmor_pem has a known algorithm
        # of RSA, that means the DER structure is of the type RSAPublicKey, so
        # we need to wrap it in the PublicKeyInfo structure.
        if algo == 'rsa':
            return keys.PublicKeyInfo.wrap(data, 'rsa')

    if key_type is None or key_type == 'public key':
        try:
            pki = keys.PublicKeyInfo.load(data)
            # Call .native to fully parse since asn1crypto is lazy
            pki.native
            return pki
        except (ValueError):
            pass  # Data was not PublicKeyInfo

        try:
            rpk = keys.RSAPublicKey.load(data)
            # Call .native to fully parse since asn1crypto is lazy
            rpk.native
            return keys.PublicKeyInfo.wrap(rpk, 'rsa')
        except (ValueError):
            pass  # Data was not an RSAPublicKey

    if key_type is None or key_type == 'certificate':
        try:
            parsed_cert = x509.Certificate.load(data)
            key_info = parsed_cert['tbs_certificate']['subject_public_key_info']
            return key_info
        except (ValueError):
            pass  # Data was not a cert

    raise ValueError('The data specified does not appear to be a known public key or certificate format')


def parse_certificate(data):
    """
    Loads a certificate from a DER or PEM-formatted file. Supports X.509
    certificates only.

    :param data:
        A byte string to load the certificate from

    :raises:
        ValueError - when the data does not appear to contain a certificate

    :return:
        An asn1crypto.x509.Certificate object
    """

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    key_type = None

    # Appears to be PEM formatted
    if data[0:5] == b'-----':
        key_type, _, data = _unarmor_pem(data)

        if key_type == 'private key':
            raise ValueError(pretty_message(
                '''
                The data specified does not appear to be a certificate, but
                rather a private key
                '''
            ))

        if key_type == 'public key':
            raise ValueError(pretty_message(
                '''
                The data specified does not appear to be a certificate, but
                rather a public key
                '''
            ))

    if key_type is None or key_type == 'certificate':
        try:
            return x509.Certificate.load(data)
        except (ValueError):
            pass  # Data was not a Certificate

    raise ValueError(pretty_message(
        '''
        The data specified does not appear to be a known certificate format
        '''
    ))


def parse_private(data, password=None):
    """
    Loads a private key from a DER or PEM-formatted file. Supports RSA, DSA and
    EC private keys. Works with the follow formats:

     - RSAPrivateKey (PKCS#1)
     - ECPrivateKey (SECG SEC1 V2)
     - DSAPrivateKey (OpenSSL)
     - PrivateKeyInfo (RSA/DSA/EC - PKCS#8)
     - EncryptedPrivateKeyInfo (RSA/DSA/EC - PKCS#8)
     - Encrypted RSAPrivateKey (PEM only, OpenSSL)
     - Encrypted DSAPrivateKey (PEM only, OpenSSL)
     - Encrypted ECPrivateKey (PEM only, OpenSSL)

    :param data:
        A byte string to load the private key from

    :param password:
        The password to unencrypt the private key

    :raises:
        ValueError - when the data does not appear to contain a private key, or the password is invalid

    :return:
        An asn1crypto.keys.PrivateKeyInfo object
    """

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    if password is not None:
        if not isinstance(password, byte_cls):
            raise TypeError(pretty_message(
                '''
                password must be a byte string, not %s
                ''',
                type_name(password)
            ))
    else:
        password = b''

    # Appears to be PEM formatted
    if data[0:5] == b'-----':
        key_type, _, data = _unarmor_pem(data, password)

        if key_type == 'public key':
            raise ValueError(pretty_message(
                '''
                The data specified does not appear to be a private key, but
                rather a public key
                '''
            ))

        if key_type == 'certificate':
            raise ValueError(pretty_message(
                '''
                The data specified does not appear to be a private key, but
                rather a certificate
                '''
            ))

    try:
        pki = keys.PrivateKeyInfo.load(data)
        # Call .native to fully parse since asn1crypto is lazy
        pki.native
        return pki
    except (ValueError):
        pass  # Data was not PrivateKeyInfo

    try:
        parsed_wrapper = keys.EncryptedPrivateKeyInfo.load(data)
        encryption_algorithm_info = parsed_wrapper['encryption_algorithm']
        encrypted_data = parsed_wrapper['encrypted_data'].native
        decrypted_data = _decrypt_encrypted_data(encryption_algorithm_info, encrypted_data, password)
        pki = keys.PrivateKeyInfo.load(decrypted_data)
        # Call .native to fully parse since asn1crypto is lazy
        pki.native
        return pki
    except (ValueError):
        pass  # Data was not EncryptedPrivateKeyInfo

    try:
        parsed = keys.RSAPrivateKey.load(data)
        # Call .native to fully parse since asn1crypto is lazy
        parsed.native
        return keys.PrivateKeyInfo.wrap(parsed, 'rsa')
    except (ValueError):
        pass  # Data was not an RSAPrivateKey

    try:
        parsed = keys.DSAPrivateKey.load(data)
        # Call .native to fully parse since asn1crypto is lazy
        parsed.native
        return keys.PrivateKeyInfo.wrap(parsed, 'dsa')
    except (ValueError):
        pass  # Data was not a DSAPrivateKey

    try:
        parsed = keys.ECPrivateKey.load(data)
        # Call .native to fully parse since asn1crypto is lazy
        parsed.native
        return keys.PrivateKeyInfo.wrap(parsed, 'ec')
    except (ValueError):
        pass  # Data was not an ECPrivateKey

    raise ValueError(pretty_message(
        '''
        The data specified does not appear to be a known private key format
        '''
    ))


def _unarmor_pem(data, password=None):
    """
    Removes PEM-encoding from a public key, private key or certificate. If the
    private key is encrypted, the password will be used to decrypt it.

    :param data:
        A byte string of the PEM-encoded data

    :param password:
        A byte string of the encryption password, or None

    :return:
        A 3-element tuple in the format: (key_type, algorithm, der_bytes). The
        key_type will be a unicode string of "public key", "private key" or
        "certificate". The algorithm will be a unicode string of "rsa", "dsa"
        or "ec".
    """

    object_type, headers, der_bytes = pem.unarmor(data)

    type_regex = '^((DSA|EC|RSA) PRIVATE KEY|ENCRYPTED PRIVATE KEY|PRIVATE KEY|PUBLIC KEY|RSA PUBLIC KEY|CERTIFICATE)'
    armor_type = re.match(type_regex, object_type)
    if not armor_type:
        raise ValueError(pretty_message(
            '''
            data does not seem to contain a PEM-encoded certificate, private
            key or public key
            '''
        ))

    pem_header = armor_type.group(1)

    data = data.strip()

    # RSA private keys are encrypted after being DER-encoded, but before base64
    # encoding, so they need to be hanlded specially
    if pem_header in set(['RSA PRIVATE KEY', 'DSA PRIVATE KEY', 'EC PRIVATE KEY']):
        algo = armor_type.group(2).lower()
        return ('private key', algo, _unarmor_pem_openssl_private(headers, der_bytes, password))

    key_type = pem_header.lower()
    algo = None
    if key_type == 'encrypted private key':
        key_type = 'private key'
    elif key_type == 'rsa public key':
        key_type = 'public key'
        algo = 'rsa'

    return (key_type, algo, der_bytes)


def _unarmor_pem_openssl_private(headers, data, password):
    """
    Parses a PKCS#1 private key, or encrypted private key

    :param headers:
        A dict of "Name: Value" lines from right after the PEM header

    :param data:
        A byte string of the DER-encoded PKCS#1 private key

    :param password:
        A byte string of the password to use if the private key is encrypted

    :return:
        A byte string of the DER-encoded private key
    """

    enc_algo = None
    enc_iv_hex = None
    enc_iv = None

    if 'DEK-Info' in headers:
        params = headers['DEK-Info']
        if params.find(',') != -1:
            enc_algo, enc_iv_hex = params.strip().split(',')
        else:
            enc_algo = 'RC4'

    if not enc_algo:
        return data

    if enc_iv_hex:
        enc_iv = binascii.unhexlify(enc_iv_hex.encode('ascii'))
    enc_algo = enc_algo.lower()

    enc_key_length = {
        'aes-128-cbc': 16,
        'aes-128': 16,
        'aes-192-cbc': 24,
        'aes-192': 24,
        'aes-256-cbc': 32,
        'aes-256': 32,
        'rc4': 16,
        'rc4-64': 8,
        'rc4-40': 5,
        'rc2-64-cbc': 8,
        'rc2-40-cbc': 5,
        'rc2-cbc': 16,
        'rc2': 16,
        'des-ede3-cbc': 24,
        'des-ede3': 24,
        'des3': 24,
        'des-ede-cbc': 16,
        'des-cbc': 8,
        'des': 8,
    }[enc_algo]

    enc_key = hashlib.md5(password + enc_iv[0:8]).digest()
    while enc_key_length > len(enc_key):
        enc_key += hashlib.md5(enc_key + password + enc_iv[0:8]).digest()
    enc_key = enc_key[0:enc_key_length]

    enc_algo_name = {
        'aes-128-cbc': 'aes',
        'aes-128': 'aes',
        'aes-192-cbc': 'aes',
        'aes-192': 'aes',
        'aes-256-cbc': 'aes',
        'aes-256': 'aes',
        'rc4': 'rc4',
        'rc4-64': 'rc4',
        'rc4-40': 'rc4',
        'rc2-64-cbc': 'rc2',
        'rc2-40-cbc': 'rc2',
        'rc2-cbc': 'rc2',
        'rc2': 'rc2',
        'des-ede3-cbc': 'tripledes',
        'des-ede3': 'tripledes',
        'des3': 'tripledes',
        'des-ede-cbc': 'tripledes',
        'des-cbc': 'des',
        'des': 'des',
    }[enc_algo]
    decrypt_func = crypto_funcs[enc_algo_name]

    if enc_algo_name == 'rc4':
        return decrypt_func(enc_key, data)

    return decrypt_func(enc_key, data, enc_iv)


def parse_pkcs12(data, password=None):
    """
    Parses a PKCS#12 ANS.1 DER-encoded structure and extracts certs and keys

    :param data:
        A byte string of a DER-encoded PKCS#12 file

    :param password:
        A byte string of the password to any encrypted data

    :raises:
        ValueError - when any of the parameters are of the wrong type or value
        OSError - when an error is returned by one of the OS decryption functions

    :return:
        A three-element tuple of:
         1. An asn1crypto.keys.PrivateKeyInfo object
         2. An asn1crypto.x509.Certificate object
         3. A list of zero or more asn1crypto.x509.Certificate objects that are
            "extra" certificates, possibly intermediates from the cert chain
    """

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    if password is not None:
        if not isinstance(password, byte_cls):
            raise TypeError(pretty_message(
                '''
                password must be a byte string, not %s
                ''',
                type_name(password)
            ))
    else:
        password = b''

    certs = {}
    private_keys = {}

    pfx = pkcs12.Pfx.load(data)

    auth_safe = pfx['auth_safe']
    if auth_safe['content_type'].native != 'data':
        raise ValueError(pretty_message(
            '''
            Only password-protected PKCS12 files are currently supported
            '''
        ))
    authenticated_safe = pfx.authenticated_safe

    mac_data = pfx['mac_data']
    if mac_data:
        mac_algo = mac_data['mac']['digest_algorithm']['algorithm'].native
        key_length = {
            'sha1': 20,
            'sha224': 28,
            'sha256': 32,
            'sha384': 48,
            'sha512': 64,
            'sha512_224': 28,
            'sha512_256': 32,
        }[mac_algo]
        mac_key = pkcs12_kdf(
            mac_algo,
            password,
            mac_data['mac_salt'].native,
            mac_data['iterations'].native,
            key_length,
            3  # ID 3 is for generating an HMAC key
        )
        hash_mod = getattr(hashlib, mac_algo)
        computed_hmac = hmac.new(mac_key, auth_safe['content'].contents, hash_mod).digest()
        stored_hmac = mac_data['mac']['digest'].native
        if not constant_compare(computed_hmac, stored_hmac):
            raise ValueError('Password provided is invalid')

    for content_info in authenticated_safe:
        content = content_info['content']

        if isinstance(content, core.OctetString):
            _parse_safe_contents(content.native, certs, private_keys, password)

        elif isinstance(content, cms.EncryptedData):
            encrypted_content_info = content['encrypted_content_info']

            encryption_algorithm_info = encrypted_content_info['content_encryption_algorithm']
            encrypted_content = encrypted_content_info['encrypted_content'].native
            decrypted_content = _decrypt_encrypted_data(encryption_algorithm_info, encrypted_content, password)

            _parse_safe_contents(decrypted_content, certs, private_keys, password)

        else:
            raise ValueError(pretty_message(
                '''
                Public-key-based PKCS12 files are not currently supported
                '''
            ))

    key_fingerprints = set(private_keys.keys())
    cert_fingerprints = set(certs.keys())

    common_fingerprints = sorted(list(key_fingerprints & cert_fingerprints))

    key = None
    cert = None
    other_certs = []

    if len(common_fingerprints) >= 1:
        fingerprint = common_fingerprints[0]
        key = private_keys[fingerprint]
        cert = certs[fingerprint]
        other_certs = [certs[f] for f in certs if f != fingerprint]
        return (key, cert, other_certs)

    if len(private_keys) > 0:
        first_key = sorted(list(private_keys.keys()))[0]
        key = private_keys[first_key]

    if len(certs) > 0:
        first_key = sorted(list(certs.keys()))[0]
        cert = certs[first_key]
        del certs[first_key]

    if len(certs) > 0:
        other_certs = sorted(list(certs.values()))

    return (key, cert, other_certs)


def _parse_safe_contents(safe_contents, certs, private_keys, password):
    """
    Parses a SafeContents PKCS#12 ANS.1 structure and extracts certs and keys

    :param safe_contents:
        A byte string of ber-encoded SafeContents, or a asn1crypto.pkcs12.SafeContents
        parsed object

    :param certs:
        A dict to store certificates in

    :param keys:
        A dict to store keys in

    :param password:
        A byte string of the password to any encrypted data
    """

    if isinstance(safe_contents, byte_cls):
        safe_contents = pkcs12.SafeContents.load(safe_contents)

    for safe_bag in safe_contents:
        bag_value = safe_bag['bag_value']

        if isinstance(bag_value, pkcs12.CertBag):
            if bag_value['cert_id'].native == 'x509':
                cert = bag_value['cert_value'].parsed
                public_key_info = cert['tbs_certificate']['subject_public_key_info']
                certs[public_key_info.fingerprint] = bag_value['cert_value'].parsed

        elif isinstance(bag_value, keys.PrivateKeyInfo):
            private_keys[bag_value.fingerprint] = bag_value

        elif isinstance(bag_value, keys.EncryptedPrivateKeyInfo):
            encryption_algorithm_info = bag_value['encryption_algorithm']
            encrypted_key_bytes = bag_value['encrypted_data'].native
            decrypted_key_bytes = _decrypt_encrypted_data(encryption_algorithm_info, encrypted_key_bytes, password)
            private_key = keys.PrivateKeyInfo.load(decrypted_key_bytes)
            private_keys[private_key.fingerprint] = private_key

        elif isinstance(bag_value, pkcs12.SafeContents):
            _parse_safe_contents(bag_value, certs, private_keys, password)

        else:
            # We don't care about CRL bags or secret bags
            pass


def _decrypt_encrypted_data(encryption_algorithm_info, encrypted_content, password):
    """
    Decrypts encrypted ASN.1 data

    :param encryption_algorithm_info:
        An instance of asn1crypto.pkcs5.Pkcs5EncryptionAlgorithm

    :param encrypted_content:
        A byte string of the encrypted content

    :param password:
        A byte string of the encrypted content's password

    :return:
        A byte string of the decrypted plaintext
    """

    decrypt_func = crypto_funcs[encryption_algorithm_info.encryption_cipher]

    # Modern, PKCS#5 PBES2-based encryption
    if encryption_algorithm_info.kdf == 'pbkdf2':

        if encryption_algorithm_info.encryption_cipher == 'rc5':
            raise ValueError(pretty_message(
                '''
                PBES2 encryption scheme utilizing RC5 encryption is not supported
                '''
            ))

        enc_key = pbkdf2(
            encryption_algorithm_info.kdf_hmac,
            password,
            encryption_algorithm_info.kdf_salt,
            encryption_algorithm_info.kdf_iterations,
            encryption_algorithm_info.key_length
        )
        enc_iv = encryption_algorithm_info.encryption_iv

        plaintext = decrypt_func(enc_key, encrypted_content, enc_iv)

    elif encryption_algorithm_info.kdf == 'pbkdf1':
        derived_output = pbkdf1(
            encryption_algorithm_info.kdf_hmac,
            password,
            encryption_algorithm_info.kdf_salt,
            encryption_algorithm_info.kdf_iterations,
            encryption_algorithm_info.key_length + 8
        )
        enc_key = derived_output[0:8]
        enc_iv = derived_output[8:16]

        plaintext = decrypt_func(enc_key, encrypted_content, enc_iv)

    elif encryption_algorithm_info.kdf == 'pkcs12_kdf':
        enc_key = pkcs12_kdf(
            encryption_algorithm_info.kdf_hmac,
            password,
            encryption_algorithm_info.kdf_salt,
            encryption_algorithm_info.kdf_iterations,
            encryption_algorithm_info.key_length,
            1  # ID 1 is for generating a key
        )

        # Since RC4 is a stream cipher, we don't use an IV
        if encryption_algorithm_info.encryption_cipher == 'rc4':
            plaintext = decrypt_func(enc_key, encrypted_content)

        else:
            enc_iv = pkcs12_kdf(
                encryption_algorithm_info.kdf_hmac,
                password,
                encryption_algorithm_info.kdf_salt,
                encryption_algorithm_info.kdf_iterations,
                encryption_algorithm_info.encryption_block_size,
                2   # ID 2 is for generating an IV
            )
            plaintext = decrypt_func(enc_key, encrypted_content, enc_iv)

    return plaintext
