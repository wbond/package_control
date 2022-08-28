# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function
from base64 import b32encode
import os
import shutil
import tempfile

from .._asn1 import (
    Certificate as Asn1Certificate,
    ECDomainParameters,
    Integer,
    KeyExchangeAlgorithm,
    Null,
    PrivateKeyInfo,
    PublicKeyAlgorithm,
    PublicKeyInfo,
    RSAPublicKey,
)
from .._asymmetric import (
    _CertificateBase,
    _fingerprint,
    _parse_pkcs12,
    _PrivateKeyBase,
    _PublicKeyBase,
    _unwrap_private_key_info,
    parse_certificate,
    parse_private,
    parse_public,
)
from .._errors import pretty_message
from .._ffi import new, unwrap, bytes_from_buffer, buffer_from_bytes, deref, null, is_null, pointer_set
from ._security import Security, SecurityConst, handle_sec_error, osx_version_info
from ._core_foundation import CoreFoundation, CFHelpers, handle_cf_error
from .util import rand_bytes
from ..errors import AsymmetricKeyError, IncompleteAsymmetricKeyError, SignatureError
from .._pkcs1 import add_pss_padding, verify_pss_padding, remove_pkcs1v15_encryption_padding
from .._types import type_name, str_cls, byte_cls, int_types


__all__ = [
    'Certificate',
    'dsa_sign',
    'dsa_verify',
    'ecdsa_sign',
    'ecdsa_verify',
    'generate_pair',
    'load_certificate',
    'load_pkcs12',
    'load_private_key',
    'load_public_key',
    'parse_pkcs12',
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


class PrivateKey(_PrivateKeyBase):
    """
    Container for the OS crypto library representation of a private key
    """

    sec_key_ref = None
    _public_key = None

    # A reference to the library used in the destructor to make sure it hasn't
    # been garbage collected by the time this object is garbage collected
    _lib = None

    def __init__(self, sec_key_ref, asn1):
        """
        :param sec_key_ref:
            A Security framework SecKeyRef value from loading/importing the
            key

        :param asn1:
            An asn1crypto.keys.PrivateKeyInfo object
        """

        self.sec_key_ref = sec_key_ref
        self.asn1 = asn1
        self._lib = CoreFoundation

    @property
    def public_key(self):
        """
        :return:
            A PublicKey object corresponding to this private key.
        """

        if self._public_key is None:
            cf_data_private = None
            try:
                # We export here so that Security.framework will fill in the EC
                # public key for us, instead of us having to compute it
                cf_data_private_pointer = new(CoreFoundation, 'CFDataRef *')
                result = Security.SecItemExport(self.sec_key_ref, 0, 0, null(), cf_data_private_pointer)
                handle_sec_error(result)
                cf_data_private = unwrap(cf_data_private_pointer)
                private_key_bytes = CFHelpers.cf_data_to_bytes(cf_data_private)

                key = parse_private(private_key_bytes)

                if key.algorithm == 'rsa':
                    public_asn1 = PublicKeyInfo({
                        'algorithm': PublicKeyAlgorithm({
                            'algorithm': 'rsa',
                            'parameters': Null()
                        }),
                        'public_key': RSAPublicKey({
                            'modulus': key['private_key'].parsed['modulus'],
                            'public_exponent': key['private_key'].parsed['public_exponent'],
                        })
                    })

                elif key.algorithm == 'dsa':
                    params = key['private_key_algorithm']['parameters']
                    public_asn1 = PublicKeyInfo({
                        'algorithm': PublicKeyAlgorithm({
                            'algorithm': 'dsa',
                            'parameters': params.copy()
                        }),
                        'public_key': Integer(pow(
                            params['g'].native,
                            key['private_key'].parsed.native,
                            params['p'].native
                        ))
                    })

                elif key.algorithm == 'ec':
                    public_asn1 = PublicKeyInfo({
                        'algorithm': PublicKeyAlgorithm({
                            'algorithm': 'ec',
                            'parameters': ECDomainParameters(
                                name='named',
                                value=self.curve
                            )
                        }),
                        'public_key': key['private_key'].parsed['public_key'],
                    })

            finally:
                if cf_data_private:
                    CoreFoundation.CFRelease(cf_data_private)

            self._public_key = _load_key(public_asn1)

        return self._public_key

    @property
    def fingerprint(self):
        """
        Creates a fingerprint that can be compared with a public key to see if
        the two form a pair.

        This fingerprint is not compatible with fingerprints generated by any
        other software.

        :return:
            A byte string that is a sha256 hash of selected components (based
            on the key type)
        """

        if self._fingerprint is None:
            self._fingerprint = _fingerprint(self.asn1, load_private_key)
        return self._fingerprint

    def __del__(self):
        if self.sec_key_ref:
            self._lib.CFRelease(self.sec_key_ref)
            self._lib = None
            self.sec_key_ref = None


class PublicKey(_PublicKeyBase):
    """
    Container for the OS crypto library representation of a public key
    """

    sec_key_ref = None

    # A reference to the library used in the destructor to make sure it hasn't
    # been garbage collected by the time this object is garbage collected
    _lib = None

    def __init__(self, sec_key_ref, asn1):
        """
        :param sec_key_ref:
            A Security framework SecKeyRef value from loading/importing the
            key

        :param asn1:
            An asn1crypto.keys.PublicKeyInfo object
        """

        self.sec_key_ref = sec_key_ref
        self.asn1 = asn1
        self._lib = CoreFoundation

    def __del__(self):
        if self.sec_key_ref:
            self._lib.CFRelease(self.sec_key_ref)
            self._lib = None
            self.sec_key_ref = None


class Certificate(_CertificateBase):
    """
    Container for the OS crypto library representation of a certificate
    """

    sec_certificate_ref = None
    _public_key = None
    _self_signed = None

    def __init__(self, sec_certificate_ref, asn1):
        """
        :param sec_certificate_ref:
            A Security framework SecCertificateRef value from loading/importing
            the certificate

        :param asn1:
            An asn1crypto.x509.Certificate object
        """

        self.sec_certificate_ref = sec_certificate_ref
        self.asn1 = asn1

    @property
    def sec_key_ref(self):
        """
        :return:
            The SecKeyRef of the public key
        """

        return self.public_key.sec_key_ref

    @property
    def public_key(self):
        """
        :return:
            The PublicKey object for the public key this certificate contains
        """

        if not self._public_key and self.sec_certificate_ref:
            if self.asn1.signature_algo == "rsassa_pss":
                # macOS doesn't like importing RSA PSS certs, so we treat it like a
                # traditional RSA cert
                asn1 = self.asn1.copy()
                asn1['tbs_certificate']['subject_public_key_info']['algorithm']['algorithm'] = 'rsa'
                temp_cert = _load_x509(asn1)
                sec_cert_ref = temp_cert.sec_certificate_ref
            else:
                sec_cert_ref = self.sec_certificate_ref

            sec_public_key_ref_pointer = new(Security, 'SecKeyRef *')
            res = Security.SecCertificateCopyPublicKey(sec_cert_ref, sec_public_key_ref_pointer)
            handle_sec_error(res)
            sec_public_key_ref = unwrap(sec_public_key_ref_pointer)
            self._public_key = PublicKey(sec_public_key_ref, self.asn1['tbs_certificate']['subject_public_key_info'])

        return self._public_key

    @property
    def self_signed(self):
        """
        :return:
            A boolean - if the certificate is self-signed
        """

        if self._self_signed is None:
            self._self_signed = False
            if self.asn1.self_signed in set(['yes', 'maybe']):

                signature_algo = self.asn1['signature_algorithm'].signature_algo
                hash_algo = self.asn1['signature_algorithm'].hash_algo

                if signature_algo == 'rsassa_pkcs1v15':
                    verify_func = rsa_pkcs1v15_verify
                elif signature_algo == 'rsassa_pss':
                    verify_func = rsa_pss_verify
                elif signature_algo == 'dsa':
                    verify_func = dsa_verify
                elif signature_algo == 'ecdsa':
                    verify_func = ecdsa_verify
                else:
                    raise OSError(pretty_message(
                        '''
                        Unable to verify the signature of the certificate since
                        it uses the unsupported algorithm %s
                        ''',
                        signature_algo
                    ))

                try:
                    verify_func(
                        self.public_key,
                        self.asn1['signature_value'].native,
                        self.asn1['tbs_certificate'].dump(),
                        hash_algo
                    )
                    self._self_signed = True
                except (SignatureError):
                    pass

        return self._self_signed

    def __del__(self):
        if self._public_key:
            self._public_key.__del__()
            self._public_key = None

        if self.sec_certificate_ref:
            CoreFoundation.CFRelease(self.sec_certificate_ref)
            self.sec_certificate_ref = None


def generate_pair(algorithm, bit_size=None, curve=None):
    """
    Generates a public/private key pair

    :param algorithm:
        The key algorithm - "rsa", "dsa" or "ec"

    :param bit_size:
        An integer - used for "rsa" and "dsa". For "rsa" the value maye be 1024,
        2048, 3072 or 4096. For "dsa" the value may be 1024.

    :param curve:
        A unicode string - used for "ec" keys. Valid values include "secp256r1",
        "secp384r1" and "secp521r1".

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A 2-element tuple of (PublicKey, PrivateKey). The contents of each key
        may be saved by calling .asn1.dump().
    """

    if algorithm not in set(['rsa', 'dsa', 'ec']):
        raise ValueError(pretty_message(
            '''
            algorithm must be one of "rsa", "dsa", "ec", not %s
            ''',
            repr(algorithm)
        ))

    if algorithm == 'rsa':
        if bit_size not in set([1024, 2048, 3072, 4096]):
            raise ValueError(pretty_message(
                '''
                bit_size must be one of 1024, 2048, 3072, 4096, not %s
                ''',
                repr(bit_size)
            ))

    elif algorithm == 'dsa':
        if bit_size not in set([1024]):
            raise ValueError(pretty_message(
                '''
                bit_size must be 1024, not %s
                ''',
                repr(bit_size)
            ))

    elif algorithm == 'ec':
        if curve not in set(['secp256r1', 'secp384r1', 'secp521r1']):
            raise ValueError(pretty_message(
                '''
                curve must be one of "secp256r1", "secp384r1", "secp521r1", not %s
                ''',
                repr(curve)
            ))

    cf_dict = None
    public_key_ref = None
    private_key_ref = None
    cf_data_public = None
    cf_data_private = None
    cf_string = None
    sec_access_ref = None
    sec_keychain_ref = None
    temp_dir = None

    try:
        alg_id = {
            'dsa': SecurityConst.CSSM_ALGID_DSA,
            'ec': SecurityConst.CSSM_ALGID_ECDSA,
            'rsa': SecurityConst.CSSM_ALGID_RSA,
        }[algorithm]

        if algorithm == 'ec':
            key_size = {
                'secp256r1': 256,
                'secp384r1': 384,
                'secp521r1': 521,
            }[curve]
        else:
            key_size = bit_size

        private_key_pointer = new(Security, 'SecKeyRef *')
        public_key_pointer = new(Security, 'SecKeyRef *')

        cf_string = CFHelpers.cf_string_from_unicode("Temporary oscrypto key")

        # We used to use SecKeyGeneratePair() for everything but DSA keys, but due to changes
        # in macOS security, we can't reliably access the default keychain, and instead
        # get an "OSError: User interaction is not allowed." result. Because of this we now
        # use SecKeyCreatePair() for everything, but we even use a throw-away keychain.
        passphrase_len = 16
        rand_data = rand_bytes(10 + passphrase_len)
        passphrase = rand_data[10:]

        temp_filename = b32encode(rand_data[:10]).decode('utf-8')
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, temp_filename).encode('utf-8')

        sec_keychain_ref_pointer = new(Security, 'SecKeychainRef *')
        result = Security.SecKeychainCreate(
            temp_path,
            passphrase_len,
            passphrase,
            False,
            null(),
            sec_keychain_ref_pointer
        )
        handle_sec_error(result)
        sec_keychain_ref = unwrap(sec_keychain_ref_pointer)

        sec_access_ref_pointer = new(Security, 'SecAccessRef *')
        result = Security.SecAccessCreate(cf_string, null(), sec_access_ref_pointer)
        handle_sec_error(result)
        sec_access_ref = unwrap(sec_access_ref_pointer)

        result = Security.SecKeyCreatePair(
            sec_keychain_ref,
            alg_id,
            key_size,
            0,
            SecurityConst.CSSM_KEYUSE_VERIFY,
            SecurityConst.CSSM_KEYATTR_EXTRACTABLE | SecurityConst.CSSM_KEYATTR_PERMANENT,
            SecurityConst.CSSM_KEYUSE_SIGN,
            SecurityConst.CSSM_KEYATTR_EXTRACTABLE | SecurityConst.CSSM_KEYATTR_PERMANENT,
            sec_access_ref,
            public_key_pointer,
            private_key_pointer
        )
        handle_sec_error(result)

        public_key_ref = unwrap(public_key_pointer)
        private_key_ref = unwrap(private_key_pointer)

        cf_data_public_pointer = new(CoreFoundation, 'CFDataRef *')
        result = Security.SecItemExport(public_key_ref, 0, 0, null(), cf_data_public_pointer)
        handle_sec_error(result)
        cf_data_public = unwrap(cf_data_public_pointer)
        public_key_bytes = CFHelpers.cf_data_to_bytes(cf_data_public)

        cf_data_private_pointer = new(CoreFoundation, 'CFDataRef *')
        result = Security.SecItemExport(private_key_ref, 0, 0, null(), cf_data_private_pointer)
        handle_sec_error(result)
        cf_data_private = unwrap(cf_data_private_pointer)
        private_key_bytes = CFHelpers.cf_data_to_bytes(cf_data_private)

        # Clean the new keys out of the keychain
        result = Security.SecKeychainItemDelete(public_key_ref)
        handle_sec_error(result)
        result = Security.SecKeychainItemDelete(private_key_ref)
        handle_sec_error(result)

    finally:
        if cf_dict:
            CoreFoundation.CFRelease(cf_dict)
        if public_key_ref:
            CoreFoundation.CFRelease(public_key_ref)
        if private_key_ref:
            CoreFoundation.CFRelease(private_key_ref)
        if cf_data_public:
            CoreFoundation.CFRelease(cf_data_public)
        if cf_data_private:
            CoreFoundation.CFRelease(cf_data_private)
        if cf_string:
            CoreFoundation.CFRelease(cf_string)
        if sec_keychain_ref:
            Security.SecKeychainDelete(sec_keychain_ref)
            CoreFoundation.CFRelease(sec_keychain_ref)
        if temp_dir:
            shutil.rmtree(temp_dir)
        if sec_access_ref:
            CoreFoundation.CFRelease(sec_access_ref)

    return (load_public_key(public_key_bytes), load_private_key(private_key_bytes))


def generate_dh_parameters(bit_size):
    """
    Generates DH parameters for use with Diffie-Hellman key exchange. Returns
    a structure in the format of DHParameter defined in PKCS#3, which is also
    used by the OpenSSL dhparam tool.

    THIS CAN BE VERY TIME CONSUMING!

    :param bit_size:
        The integer bit size of the parameters to generate. Must be between 512
        and 4096, and divisible by 64. Recommended secure value as of early 2016
        is 2048, with an absolute minimum of 1024.

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        An asn1crypto.algos.DHParameters object. Use
        oscrypto.asymmetric.dump_dh_parameters() to save to disk for usage with
        web servers.
    """

    if not isinstance(bit_size, int_types):
        raise TypeError(pretty_message(
            '''
            bit_size must be an integer, not %s
            ''',
            type_name(bit_size)
        ))

    if bit_size < 512:
        raise ValueError('bit_size must be greater than or equal to 512')

    if bit_size > 4096:
        raise ValueError('bit_size must be less than or equal to 4096')

    if bit_size % 64 != 0:
        raise ValueError('bit_size must be a multiple of 64')

    public_key_ref = None
    private_key_ref = None
    cf_data_public = None
    cf_data_private = None
    cf_string = None
    sec_keychain_ref = None
    sec_access_ref = None
    temp_dir = None

    try:
        public_key_pointer = new(Security, 'SecKeyRef *')
        private_key_pointer = new(Security, 'SecKeyRef *')

        cf_string = CFHelpers.cf_string_from_unicode("Temporary oscrypto key")

        passphrase_len = 16
        rand_data = rand_bytes(10 + passphrase_len)
        passphrase = rand_data[10:]

        temp_filename = b32encode(rand_data[:10]).decode('utf-8')
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, temp_filename).encode('utf-8')

        sec_keychain_ref_pointer = new(Security, 'SecKeychainRef *')
        result = Security.SecKeychainCreate(
            temp_path,
            passphrase_len,
            passphrase,
            False,
            null(),
            sec_keychain_ref_pointer
        )
        handle_sec_error(result)
        sec_keychain_ref = unwrap(sec_keychain_ref_pointer)

        sec_access_ref_pointer = new(Security, 'SecAccessRef *')
        result = Security.SecAccessCreate(cf_string, null(), sec_access_ref_pointer)
        handle_sec_error(result)
        sec_access_ref = unwrap(sec_access_ref_pointer)

        result = Security.SecKeyCreatePair(
            sec_keychain_ref,
            SecurityConst.CSSM_ALGID_DH,
            bit_size,
            0,
            0,
            SecurityConst.CSSM_KEYATTR_EXTRACTABLE | SecurityConst.CSSM_KEYATTR_PERMANENT,
            0,
            SecurityConst.CSSM_KEYATTR_EXTRACTABLE | SecurityConst.CSSM_KEYATTR_PERMANENT,
            sec_access_ref,
            public_key_pointer,
            private_key_pointer
        )
        handle_sec_error(result)

        public_key_ref = unwrap(public_key_pointer)
        private_key_ref = unwrap(private_key_pointer)

        cf_data_private_pointer = new(CoreFoundation, 'CFDataRef *')
        result = Security.SecItemExport(private_key_ref, 0, 0, null(), cf_data_private_pointer)
        handle_sec_error(result)
        cf_data_private = unwrap(cf_data_private_pointer)
        private_key_bytes = CFHelpers.cf_data_to_bytes(cf_data_private)

        # Clean the new keys out of the keychain
        result = Security.SecKeychainItemDelete(public_key_ref)
        handle_sec_error(result)

        result = Security.SecKeychainItemDelete(private_key_ref)
        handle_sec_error(result)

        return KeyExchangeAlgorithm.load(private_key_bytes)['parameters']

    finally:
        if public_key_ref:
            CoreFoundation.CFRelease(public_key_ref)
        if private_key_ref:
            CoreFoundation.CFRelease(private_key_ref)
        if cf_data_public:
            CoreFoundation.CFRelease(cf_data_public)
        if cf_data_private:
            CoreFoundation.CFRelease(cf_data_private)
        if cf_string:
            CoreFoundation.CFRelease(cf_string)
        if sec_keychain_ref:
            Security.SecKeychainDelete(sec_keychain_ref)
            CoreFoundation.CFRelease(sec_keychain_ref)
        if temp_dir:
            shutil.rmtree(temp_dir)
        if sec_access_ref:
            CoreFoundation.CFRelease(sec_access_ref)


def load_certificate(source):
    """
    Loads an x509 certificate into a Certificate object

    :param source:
        A byte string of file contents, a unicode string filename or an
        asn1crypto.x509.Certificate object

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A Certificate object
    """

    if isinstance(source, Asn1Certificate):
        certificate = source

    elif isinstance(source, byte_cls):
        certificate = parse_certificate(source)

    elif isinstance(source, str_cls):
        with open(source, 'rb') as f:
            certificate = parse_certificate(f.read())

    else:
        raise TypeError(pretty_message(
            '''
            source must be a byte string, unicode string or
            asn1crypto.x509.Certificate object, not %s
            ''',
            type_name(source)
        ))

    return _load_x509(certificate)


def _load_x509(certificate):
    """
    Loads an ASN.1 object of an x509 certificate into a Certificate object

    :param certificate:
        An asn1crypto.x509.Certificate object

    :return:
        A Certificate object
    """

    source = certificate.dump()

    cf_source = None
    try:
        cf_source = CFHelpers.cf_data_from_bytes(source)
        sec_key_ref = Security.SecCertificateCreateWithData(CoreFoundation.kCFAllocatorDefault, cf_source)
        return Certificate(sec_key_ref, certificate)

    finally:
        if cf_source:
            CoreFoundation.CFRelease(cf_source)


def load_private_key(source, password=None):
    """
    Loads a private key into a PrivateKey object

    :param source:
        A byte string of file contents, a unicode string filename or an
        asn1crypto.keys.PrivateKeyInfo object

    :param password:
        A byte or unicode string to decrypt the private key file. Unicode
        strings will be encoded using UTF-8. Not used is the source is a
        PrivateKeyInfo object.

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        oscrypto.errors.AsymmetricKeyError - when the private key is incompatible with the OS crypto library
        OSError - when an error is returned by the OS crypto library

    :return:
        A PrivateKey object
    """

    if isinstance(source, PrivateKeyInfo):
        private_object = source

    else:
        if password is not None:
            if isinstance(password, str_cls):
                password = password.encode('utf-8')
            if not isinstance(password, byte_cls):
                raise TypeError(pretty_message(
                    '''
                    password must be a byte string, not %s
                    ''',
                    type_name(password)
                ))

        if isinstance(source, str_cls):
            with open(source, 'rb') as f:
                source = f.read()

        elif not isinstance(source, byte_cls):
            raise TypeError(pretty_message(
                '''
                source must be a byte string, unicode string or
                asn1crypto.keys.PrivateKeyInfo object, not %s
                ''',
                type_name(source)
            ))

        private_object = parse_private(source, password)

    return _load_key(private_object)


def load_public_key(source):
    """
    Loads a public key into a PublicKey object

    :param source:
        A byte string of file contents, a unicode string filename or an
        asn1crypto.keys.PublicKeyInfo object

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        oscrypto.errors.AsymmetricKeyError - when the public key is incompatible with the OS crypto library
        OSError - when an error is returned by the OS crypto library

    :return:
        A PublicKey object
    """

    if isinstance(source, PublicKeyInfo):
        public_key = source

    elif isinstance(source, byte_cls):
        public_key = parse_public(source)

    elif isinstance(source, str_cls):
        with open(source, 'rb') as f:
            public_key = parse_public(f.read())

    else:
        raise TypeError(pretty_message(
            '''
            source must be a byte string, unicode string or
            asn1crypto.keys.PublicKeyInfo object, not %s
            ''',
            type_name(source)
        ))

    return _load_key(public_key)


def _load_key(key_object):
    """
    Common code to load public and private keys into PublicKey and PrivateKey
    objects

    :param key_object:
        An asn1crypto.keys.PublicKeyInfo or asn1crypto.keys.PrivateKeyInfo
        object

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        oscrypto.errors.AsymmetricKeyError - when the key is incompatible with the OS crypto library
        OSError - when an error is returned by the OS crypto library

    :return:
        A PublicKey or PrivateKey object
    """

    if key_object.algorithm == 'ec':
        curve_type, details = key_object.curve
        if curve_type != 'named':
            raise AsymmetricKeyError('OS X only supports EC keys using named curves')
        if details not in set(['secp256r1', 'secp384r1', 'secp521r1']):
            raise AsymmetricKeyError(pretty_message(
                '''
                OS X only supports EC keys using the named curves secp256r1,
                secp384r1 and secp521r1
                '''
            ))

    elif key_object.algorithm == 'dsa' and key_object.hash_algo == 'sha2':
        raise AsymmetricKeyError(pretty_message(
            '''
            OS X only supports DSA keys based on SHA1 (2048 bits or less) - this
            key is based on SHA2 and is %s bits
            ''',
            key_object.bit_size
        ))

    elif key_object.algorithm == 'dsa' and key_object.hash_algo is None:
        raise IncompleteAsymmetricKeyError(pretty_message(
            '''
            The DSA key does not contain the necessary p, q and g parameters
            and can not be used
            '''
        ))

    if isinstance(key_object, PublicKeyInfo):
        if key_object.algorithm == 'rsassa_pss':
            # We have to masquerade an RSA PSS key as plain RSA or it won't
            # import properly
            temp_key_object = key_object.copy()
            temp_key_object['algorithm']['algorithm'] = 'rsa'
            source = temp_key_object.dump()
        else:
            source = key_object.dump()
        item_type = SecurityConst.kSecItemTypePublicKey

    else:
        source = _unwrap_private_key_info(key_object).dump()
        item_type = SecurityConst.kSecItemTypePrivateKey

    cf_source = None
    keys_array = None
    attr_array = None

    try:
        cf_source = CFHelpers.cf_data_from_bytes(source)

        format_pointer = new(Security, 'uint32_t *')
        pointer_set(format_pointer, SecurityConst.kSecFormatOpenSSL)
        type_pointer = new(Security, 'uint32_t *')
        pointer_set(type_pointer, item_type)
        keys_pointer = new(CoreFoundation, 'CFArrayRef *')

        attr_array = CFHelpers.cf_array_from_list([
            Security.kSecAttrIsExtractable
        ])

        import_export_params_pointer = new(Security, 'SecItemImportExportKeyParameters *')
        import_export_params = unwrap(import_export_params_pointer)
        import_export_params.version = 0
        import_export_params.flags = 0
        import_export_params.passphrase = null()
        import_export_params.alertTitle = null()
        import_export_params.alertPrompt = null()
        import_export_params.accessRef = null()
        import_export_params.keyUsage = null()
        import_export_params.keyAttributes = attr_array

        res = Security.SecItemImport(
            cf_source,
            null(),
            format_pointer,
            type_pointer,
            0,
            import_export_params_pointer,
            null(),
            keys_pointer
        )
        handle_sec_error(res)
        keys_array = unwrap(keys_pointer)

        length = CoreFoundation.CFArrayGetCount(keys_array)
        if length > 0:
            sec_key_ref = CoreFoundation.CFArrayGetValueAtIndex(keys_array, 0)
            CoreFoundation.CFRetain(sec_key_ref)

        if item_type == SecurityConst.kSecItemTypePublicKey:
            return PublicKey(sec_key_ref, key_object)

        if item_type == SecurityConst.kSecItemTypePrivateKey:
            return PrivateKey(sec_key_ref, key_object)

    finally:
        if attr_array:
            CoreFoundation.CFRelease(attr_array)
        if keys_array:
            CoreFoundation.CFRelease(keys_array)
        if cf_source:
            CoreFoundation.CFRelease(cf_source)


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

    return _parse_pkcs12(data, password, load_private_key)


def load_pkcs12(source, password=None):
    """
    Loads a .p12 or .pfx file into a PrivateKey object and one or more
    Certificates objects

    :param source:
        A byte string of file contents or a unicode string filename

    :param password:
        A byte or unicode string to decrypt the PKCS12 file. Unicode strings
        will be encoded using UTF-8.

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        oscrypto.errors.AsymmetricKeyError - when a contained key is incompatible with the OS crypto library
        OSError - when an error is returned by the OS crypto library

    :return:
        A three-element tuple containing (PrivateKey, Certificate, [Certificate, ...])
    """

    if password is not None:
        if isinstance(password, str_cls):
            password = password.encode('utf-8')
        if not isinstance(password, byte_cls):
            raise TypeError(pretty_message(
                '''
                password must be a byte string, not %s
                ''',
                type_name(password)
            ))

    if isinstance(source, str_cls):
        with open(source, 'rb') as f:
            source = f.read()

    elif not isinstance(source, byte_cls):
        raise TypeError(pretty_message(
            '''
            source must be a byte string or a unicode string, not %s
            ''',
            type_name(source)
        ))

    key_info, cert_info, extra_certs_info = parse_pkcs12(source, password)

    key = None
    cert = None

    if key_info:
        key = _load_key(key_info)

    if cert_info:
        cert = _load_x509(cert_info)

    extra_certs = [_load_x509(info) for info in extra_certs_info]

    return (key, cert, extra_certs)


def rsa_pkcs1v15_encrypt(certificate_or_public_key, data):
    """
    Encrypts a byte string using an RSA public key or certificate. Uses PKCS#1
    v1.5 padding.

    :param certificate_or_public_key:
        A PublicKey or Certificate object

    :param data:
        A byte string, with a maximum length 11 bytes less than the key length
        (in bytes)

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the encrypted data
    """

    if not isinstance(certificate_or_public_key, (Certificate, PublicKey)):
        raise TypeError(pretty_message(
            '''
            certificate_or_public_key must be an instance of the Certificate or
            PublicKey class, not %s
            ''',
            type_name(certificate_or_public_key)
        ))

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    key_length = certificate_or_public_key.byte_size
    buffer = buffer_from_bytes(key_length)
    output_length = new(Security, 'size_t *', key_length)
    result = Security.SecKeyEncrypt(
        certificate_or_public_key.sec_key_ref,
        SecurityConst.kSecPaddingPKCS1,
        data,
        len(data),
        buffer,
        output_length
    )
    handle_sec_error(result)

    return bytes_from_buffer(buffer, deref(output_length))


def rsa_pkcs1v15_decrypt(private_key, ciphertext):
    """
    Decrypts a byte string using an RSA private key. Uses PKCS#1 v1.5 padding.

    :param private_key:
        A PrivateKey object

    :param ciphertext:
        A byte string of the encrypted data

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the original plaintext
    """

    if not isinstance(private_key, PrivateKey):
        raise TypeError(pretty_message(
            '''
            private_key must an instance of the PrivateKey class, not %s
            ''',
            type_name(private_key)
        ))

    if not isinstance(ciphertext, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(ciphertext)
        ))

    key_length = private_key.byte_size
    buffer = buffer_from_bytes(key_length)
    output_length = new(Security, 'size_t *', key_length)

    if osx_version_info < (10, 8):
        padding = SecurityConst.kSecPaddingNone
    else:
        padding = SecurityConst.kSecPaddingPKCS1

    result = Security.SecKeyDecrypt(
        private_key.sec_key_ref,
        padding,
        ciphertext,
        len(ciphertext),
        buffer,
        output_length
    )
    handle_sec_error(result)

    output = bytes_from_buffer(buffer, deref(output_length))

    if osx_version_info < (10, 8):
        output = remove_pkcs1v15_encryption_padding(key_length, output)

    return output


def rsa_oaep_encrypt(certificate_or_public_key, data):
    """
    Encrypts a byte string using an RSA public key or certificate. Uses PKCS#1
    OAEP padding with SHA1.

    :param certificate_or_public_key:
        A PublicKey or Certificate object

    :param data:
        A byte string, with a maximum length 41 bytes (or more) less than the
        key length (in bytes)

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the encrypted data
    """

    return _encrypt(certificate_or_public_key, data, Security.kSecPaddingOAEPKey)


def rsa_oaep_decrypt(private_key, ciphertext):
    """
    Decrypts a byte string using an RSA private key. Uses PKCS#1 OAEP padding
    with SHA1.

    :param private_key:
        A PrivateKey object

    :param ciphertext:
        A byte string of the encrypted data

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the original plaintext
    """

    return _decrypt(private_key, ciphertext, Security.kSecPaddingOAEPKey)


def _encrypt(certificate_or_public_key, data, padding):
    """
    Encrypts plaintext using an RSA public key or certificate

    :param certificate_or_public_key:
        A Certificate or PublicKey object

    :param data:
        The plaintext - a byte string

    :param padding:
        The padding mode to use, specified as a kSecPadding*Key value

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the ciphertext
    """

    if not isinstance(certificate_or_public_key, (Certificate, PublicKey)):
        raise TypeError(pretty_message(
            '''
            certificate_or_public_key must be an instance of the Certificate or
            PublicKey class, not %s
            ''',
            type_name(certificate_or_public_key)
        ))

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    if not padding:
        raise ValueError('padding must be specified')

    cf_data = None
    sec_transform = None

    try:
        cf_data = CFHelpers.cf_data_from_bytes(data)

        error_pointer = new(CoreFoundation, 'CFErrorRef *')
        sec_transform = Security.SecEncryptTransformCreate(
            certificate_or_public_key.sec_key_ref,
            error_pointer
        )
        handle_cf_error(error_pointer)

        if padding:
            Security.SecTransformSetAttribute(
                sec_transform,
                Security.kSecPaddingKey,
                padding,
                error_pointer
            )
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
        if cf_data:
            CoreFoundation.CFRelease(cf_data)
        if sec_transform:
            CoreFoundation.CFRelease(sec_transform)


def _decrypt(private_key, ciphertext, padding):
    """
    Decrypts RSA ciphertext using a private key

    :param private_key:
        A PrivateKey object

    :param ciphertext:
        The ciphertext - a byte string

    :param padding:
        The padding mode to use, specified as a kSecPadding*Key value

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the plaintext
    """

    if not isinstance(private_key, PrivateKey):
        raise TypeError(pretty_message(
            '''
            private_key must be an instance of the PrivateKey class, not %s
            ''',
            type_name(private_key)
        ))

    if not isinstance(ciphertext, byte_cls):
        raise TypeError(pretty_message(
            '''
            ciphertext must be a byte string, not %s
            ''',
            type_name(ciphertext)
        ))

    if not padding:
        raise ValueError('padding must be specified')

    cf_data = None
    sec_transform = None

    try:
        cf_data = CFHelpers.cf_data_from_bytes(ciphertext)

        error_pointer = new(CoreFoundation, 'CFErrorRef *')
        sec_transform = Security.SecDecryptTransformCreate(
            private_key.sec_key_ref,
            error_pointer
        )
        handle_cf_error(error_pointer)

        Security.SecTransformSetAttribute(
            sec_transform,
            Security.kSecPaddingKey,
            padding,
            error_pointer
        )
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
        if cf_data:
            CoreFoundation.CFRelease(cf_data)
        if sec_transform:
            CoreFoundation.CFRelease(sec_transform)


def rsa_pkcs1v15_verify(certificate_or_public_key, signature, data, hash_algorithm):
    """
    Verifies an RSASSA-PKCS-v1.5 signature.

    When the hash_algorithm is "raw", the operation is identical to RSA
    public key decryption. That is: the data is not hashed and no ASN.1
    structure with an algorithm identifier of the hash algorithm is placed in
    the encrypted byte string.

    :param certificate_or_public_key:
        A Certificate or PublicKey instance to verify the signature with

    :param signature:
        A byte string of the signature to verify

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha224", "sha256", "sha384", "sha512" or "raw"

    :raises:
        oscrypto.errors.SignatureError - when the signature is determined to be invalid
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library
    """

    if certificate_or_public_key.algorithm != 'rsa':
        raise ValueError('The key specified is not an RSA public key')

    return _verify(certificate_or_public_key, signature, data, hash_algorithm)


def rsa_pss_verify(certificate_or_public_key, signature, data, hash_algorithm):
    """
    Verifies an RSASSA-PSS signature. For the PSS padding the mask gen algorithm
    will be mgf1 using the same hash algorithm as the signature. The salt length
    with be the length of the hash algorithm, and the trailer field with be the
    standard 0xBC byte.

    :param certificate_or_public_key:
        A Certificate or PublicKey instance to verify the signature with

    :param signature:
        A byte string of the signature to verify

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha224", "sha256", "sha384" or "sha512"

    :raises:
        oscrypto.errors.SignatureError - when the signature is determined to be invalid
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library
    """

    if not isinstance(certificate_or_public_key, (Certificate, PublicKey)):
        raise TypeError(pretty_message(
            '''
            certificate_or_public_key must be an instance of the Certificate or
            PublicKey class, not %s
            ''',
            type_name(certificate_or_public_key)
        ))

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    cp_algo = certificate_or_public_key.algorithm
    if cp_algo != 'rsa' and cp_algo != 'rsassa_pss':
        raise ValueError('The key specified is not an RSA public key')

    hash_length = {
        'sha1': 20,
        'sha224': 28,
        'sha256': 32,
        'sha384': 48,
        'sha512': 64
    }.get(hash_algorithm, 0)

    key_length = certificate_or_public_key.byte_size
    buffer = buffer_from_bytes(key_length)
    output_length = new(Security, 'size_t *', key_length)
    result = Security.SecKeyEncrypt(
        certificate_or_public_key.sec_key_ref,
        SecurityConst.kSecPaddingNone,
        signature,
        len(signature),
        buffer,
        output_length
    )
    handle_sec_error(result)

    plaintext = bytes_from_buffer(buffer, deref(output_length))
    if not verify_pss_padding(hash_algorithm, hash_length, certificate_or_public_key.bit_size, data, plaintext):
        raise SignatureError('Signature is invalid')


def dsa_verify(certificate_or_public_key, signature, data, hash_algorithm):
    """
    Verifies a DSA signature

    :param certificate_or_public_key:
        A Certificate or PublicKey instance to verify the signature with

    :param signature:
        A byte string of the signature to verify

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha224", "sha256", "sha384" or "sha512"

    :raises:
        oscrypto.errors.SignatureError - when the signature is determined to be invalid
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library
    """

    if certificate_or_public_key.algorithm != 'dsa':
        raise ValueError('The key specified is not a DSA public key')

    return _verify(certificate_or_public_key, signature, data, hash_algorithm)


def ecdsa_verify(certificate_or_public_key, signature, data, hash_algorithm):
    """
    Verifies an ECDSA signature

    :param certificate_or_public_key:
        A Certificate or PublicKey instance to verify the signature with

    :param signature:
        A byte string of the signature to verify

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha224", "sha256", "sha384" or "sha512"

    :raises:
        oscrypto.errors.SignatureError - when the signature is determined to be invalid
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library
    """

    if certificate_or_public_key.algorithm != 'ec':
        raise ValueError('The key specified is not an EC public key')

    return _verify(certificate_or_public_key, signature, data, hash_algorithm)


def _verify(certificate_or_public_key, signature, data, hash_algorithm):
    """
    Verifies an RSA, DSA or ECDSA signature

    :param certificate_or_public_key:
        A Certificate or PublicKey instance to verify the signature with

    :param signature:
        A byte string of the signature to verify

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha224", "sha256", "sha384" or "sha512"

    :raises:
        oscrypto.errors.SignatureError - when the signature is determined to be invalid
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library
    """

    if not isinstance(certificate_or_public_key, (Certificate, PublicKey)):
        raise TypeError(pretty_message(
            '''
            certificate_or_public_key must be an instance of the Certificate or
            PublicKey class, not %s
            ''',
            type_name(certificate_or_public_key)
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

    valid_hash_algorithms = set(['md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512'])
    if certificate_or_public_key.algorithm == 'rsa':
        valid_hash_algorithms |= set(['raw'])

    if hash_algorithm not in valid_hash_algorithms:
        valid_hash_algorithms_error = '"md5", "sha1", "sha224", "sha256", "sha384", "sha512"'
        if certificate_or_public_key.algorithm == 'rsa':
            valid_hash_algorithms_error += ', "raw"'
        raise ValueError(pretty_message(
            '''
            hash_algorithm must be one of %s, not %s
            ''',
            valid_hash_algorithms_error,
            repr(hash_algorithm)
        ))

    if certificate_or_public_key.algorithm == 'rsa' and hash_algorithm == 'raw':
        if len(data) > certificate_or_public_key.byte_size - 11:
            raise ValueError(pretty_message(
                '''
                data must be 11 bytes shorter than the key size when
                hash_algorithm is "raw" - key size is %s bytes, but data
                is %s bytes long
                ''',
                certificate_or_public_key.byte_size,
                len(data)
            ))

        result = Security.SecKeyRawVerify(
            certificate_or_public_key.sec_key_ref,
            SecurityConst.kSecPaddingPKCS1,
            data,
            len(data),
            signature,
            len(signature)
        )
        # errSSLCrypto is returned in some situations on macOS 10.12
        if result == SecurityConst.errSecVerifyFailed or result == SecurityConst.errSSLCrypto:
            raise SignatureError('Signature is invalid')
        handle_sec_error(result)
        return

    cf_signature = None
    cf_data = None
    cf_hash_length = None
    sec_transform = None

    try:
        error_pointer = new(CoreFoundation, 'CFErrorRef *')
        cf_signature = CFHelpers.cf_data_from_bytes(signature)
        sec_transform = Security.SecVerifyTransformCreate(
            certificate_or_public_key.sec_key_ref,
            cf_signature,
            error_pointer
        )
        handle_cf_error(error_pointer)

        hash_constant = {
            'md5': Security.kSecDigestMD5,
            'sha1': Security.kSecDigestSHA1,
            'sha224': Security.kSecDigestSHA2,
            'sha256': Security.kSecDigestSHA2,
            'sha384': Security.kSecDigestSHA2,
            'sha512': Security.kSecDigestSHA2
        }[hash_algorithm]

        Security.SecTransformSetAttribute(
            sec_transform,
            Security.kSecDigestTypeAttribute,
            hash_constant,
            error_pointer
        )
        handle_cf_error(error_pointer)

        if hash_algorithm in set(['sha224', 'sha256', 'sha384', 'sha512']):
            hash_length = {
                'sha224': 224,
                'sha256': 256,
                'sha384': 384,
                'sha512': 512
            }[hash_algorithm]

            cf_hash_length = CFHelpers.cf_number_from_integer(hash_length)

            Security.SecTransformSetAttribute(
                sec_transform,
                Security.kSecDigestLengthAttribute,
                cf_hash_length,
                error_pointer
            )
            handle_cf_error(error_pointer)

        if certificate_or_public_key.algorithm == 'rsa':
            Security.SecTransformSetAttribute(
                sec_transform,
                Security.kSecPaddingKey,
                Security.kSecPaddingPKCS1Key,
                error_pointer
            )
            handle_cf_error(error_pointer)

        cf_data = CFHelpers.cf_data_from_bytes(data)
        Security.SecTransformSetAttribute(
            sec_transform,
            Security.kSecTransformInputAttributeName,
            cf_data,
            error_pointer
        )
        handle_cf_error(error_pointer)

        res = Security.SecTransformExecute(sec_transform, error_pointer)
        if not is_null(error_pointer):
            error = unwrap(error_pointer)
            if not is_null(error):
                raise SignatureError('Signature is invalid')

        res = bool(CoreFoundation.CFBooleanGetValue(res))

        if not res:
            raise SignatureError('Signature is invalid')

    finally:
        if sec_transform:
            CoreFoundation.CFRelease(sec_transform)
        if cf_signature:
            CoreFoundation.CFRelease(cf_signature)
        if cf_data:
            CoreFoundation.CFRelease(cf_data)
        if cf_hash_length:
            CoreFoundation.CFRelease(cf_hash_length)


def rsa_pkcs1v15_sign(private_key, data, hash_algorithm):
    """
    Generates an RSASSA-PKCS-v1.5 signature.

    When the hash_algorithm is "raw", the operation is identical to RSA
    private key encryption. That is: the data is not hashed and no ASN.1
    structure with an algorithm identifier of the hash algorithm is placed in
    the encrypted byte string.

    :param private_key:
        The PrivateKey to generate the signature with

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha224", "sha256", "sha384",
        "sha512" or "raw"

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the signature
    """

    if private_key.algorithm != 'rsa':
        raise ValueError('The key specified is not an RSA private key')

    return _sign(private_key, data, hash_algorithm)


def rsa_pss_sign(private_key, data, hash_algorithm):
    """
    Generates an RSASSA-PSS signature. For the PSS padding the mask gen
    algorithm will be mgf1 using the same hash algorithm as the signature. The
    salt length with be the length of the hash algorithm, and the trailer field
    with be the standard 0xBC byte.

    :param private_key:
        The PrivateKey to generate the signature with

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha224", "sha256", "sha384" or
        "sha512"

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the signature
    """

    if not isinstance(private_key, PrivateKey):
        raise TypeError(pretty_message(
            '''
            private_key must be an instance of the PrivateKey class, not %s
            ''',
            type_name(private_key)
        ))

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    pk_algo = private_key.algorithm
    if pk_algo != 'rsa' and pk_algo != 'rsassa_pss':
        raise ValueError('The key specified is not an RSA private key')

    hash_length = {
        'sha1': 20,
        'sha224': 28,
        'sha256': 32,
        'sha384': 48,
        'sha512': 64
    }.get(hash_algorithm, 0)

    encoded_data = add_pss_padding(hash_algorithm, hash_length, private_key.bit_size, data)

    key_length = private_key.byte_size
    buffer = buffer_from_bytes(key_length)
    output_length = new(Security, 'size_t *', key_length)
    result = Security.SecKeyDecrypt(
        private_key.sec_key_ref,
        SecurityConst.kSecPaddingNone,
        encoded_data,
        len(encoded_data),
        buffer,
        output_length
    )
    handle_sec_error(result)

    return bytes_from_buffer(buffer, deref(output_length))


def dsa_sign(private_key, data, hash_algorithm):
    """
    Generates a DSA signature

    :param private_key:
        The PrivateKey to generate the signature with

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha224", "sha256", "sha384" or
        "sha512"

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the signature
    """

    if private_key.algorithm != 'dsa':
        raise ValueError('The key specified is not a DSA private key')

    return _sign(private_key, data, hash_algorithm)


def ecdsa_sign(private_key, data, hash_algorithm):
    """
    Generates an ECDSA signature

    :param private_key:
        The PrivateKey to generate the signature with

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha224", "sha256", "sha384" or
        "sha512"

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the signature
    """

    if private_key.algorithm != 'ec':
        raise ValueError('The key specified is not an EC private key')

    return _sign(private_key, data, hash_algorithm)


def _sign(private_key, data, hash_algorithm):
    """
    Generates an RSA, DSA or ECDSA signature

    :param private_key:
        The PrivateKey to generate the signature with

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha224", "sha256", "sha384" or
        "sha512"

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the signature
    """

    if not isinstance(private_key, PrivateKey):
        raise TypeError(pretty_message(
            '''
            private_key must be an instance of PrivateKey, not %s
            ''',
            type_name(private_key)
        ))

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    valid_hash_algorithms = set(['md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512'])
    if private_key.algorithm == 'rsa':
        valid_hash_algorithms |= set(['raw'])

    if hash_algorithm not in valid_hash_algorithms:
        valid_hash_algorithms_error = '"md5", "sha1", "sha224", "sha256", "sha384", "sha512"'
        if private_key.algorithm == 'rsa':
            valid_hash_algorithms_error += ', "raw"'
        raise ValueError(pretty_message(
            '''
            hash_algorithm must be one of %s, not %s
            ''',
            valid_hash_algorithms_error,
            repr(hash_algorithm)
        ))

    if private_key.algorithm == 'rsa' and hash_algorithm == 'raw':
        if len(data) > private_key.byte_size - 11:
            raise ValueError(pretty_message(
                '''
                data must be 11 bytes shorter than the key size when
                hash_algorithm is "raw" - key size is %s bytes, but
                data is %s bytes long
                ''',
                private_key.byte_size,
                len(data)
            ))

        key_length = private_key.byte_size
        buffer = buffer_from_bytes(key_length)
        output_length = new(Security, 'size_t *', key_length)
        result = Security.SecKeyRawSign(
            private_key.sec_key_ref,
            SecurityConst.kSecPaddingPKCS1,
            data,
            len(data),
            buffer,
            output_length
        )
        handle_sec_error(result)

        return bytes_from_buffer(buffer, deref(output_length))

    cf_signature = None
    cf_data = None
    cf_hash_length = None
    sec_transform = None

    try:
        error_pointer = new(CoreFoundation, 'CFErrorRef *')
        sec_transform = Security.SecSignTransformCreate(private_key.sec_key_ref, error_pointer)
        handle_cf_error(error_pointer)

        hash_constant = {
            'md5': Security.kSecDigestMD5,
            'sha1': Security.kSecDigestSHA1,
            'sha224': Security.kSecDigestSHA2,
            'sha256': Security.kSecDigestSHA2,
            'sha384': Security.kSecDigestSHA2,
            'sha512': Security.kSecDigestSHA2
        }[hash_algorithm]

        Security.SecTransformSetAttribute(
            sec_transform,
            Security.kSecDigestTypeAttribute,
            hash_constant,
            error_pointer
        )
        handle_cf_error(error_pointer)

        if hash_algorithm in set(['sha224', 'sha256', 'sha384', 'sha512']):
            hash_length = {
                'sha224': 224,
                'sha256': 256,
                'sha384': 384,
                'sha512': 512
            }[hash_algorithm]

            cf_hash_length = CFHelpers.cf_number_from_integer(hash_length)

            Security.SecTransformSetAttribute(
                sec_transform,
                Security.kSecDigestLengthAttribute,
                cf_hash_length,
                error_pointer
            )
            handle_cf_error(error_pointer)

        if private_key.algorithm == 'rsa':
            Security.SecTransformSetAttribute(
                sec_transform,
                Security.kSecPaddingKey,
                Security.kSecPaddingPKCS1Key,
                error_pointer
            )
            handle_cf_error(error_pointer)

        cf_data = CFHelpers.cf_data_from_bytes(data)
        Security.SecTransformSetAttribute(
            sec_transform,
            Security.kSecTransformInputAttributeName,
            cf_data,
            error_pointer
        )
        handle_cf_error(error_pointer)

        cf_signature = Security.SecTransformExecute(sec_transform, error_pointer)
        handle_cf_error(error_pointer)

        return CFHelpers.cf_data_to_bytes(cf_signature)

    finally:
        if sec_transform:
            CoreFoundation.CFRelease(sec_transform)
        if cf_signature:
            CoreFoundation.CFRelease(cf_signature)
        if cf_data:
            CoreFoundation.CFRelease(cf_data)
        if cf_hash_length:
            CoreFoundation.CFRelease(cf_hash_length)
