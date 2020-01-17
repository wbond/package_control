# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

# This file exists strictly to make it easier to vendor a combination of
# oscrypto and asn1crypto

from ..asn1crypto import algos, cms, core, keys, pem, pkcs12, util, x509

DHParameters = algos.DHParameters
DSASignature = algos.DSASignature
KeyExchangeAlgorithm = algos.KeyExchangeAlgorithm
Pbkdf2Salt = algos.Pbkdf2Salt

EncryptedData = cms.EncryptedData

Integer = core.Integer
Null = core.Null
OctetString = core.OctetString

DSAParams = keys.DSAParams
DSAPrivateKey = keys.DSAPrivateKey
ECDomainParameters = keys.ECDomainParameters
ECPointBitString = keys.ECPointBitString
ECPrivateKey = keys.ECPrivateKey
EncryptedPrivateKeyInfo = keys.EncryptedPrivateKeyInfo
PrivateKeyAlgorithm = keys.PrivateKeyAlgorithm
PrivateKeyInfo = keys.PrivateKeyInfo
PublicKeyAlgorithm = keys.PublicKeyAlgorithm
PublicKeyInfo = keys.PublicKeyInfo
RSAPrivateKey = keys.RSAPrivateKey
RSAPublicKey = keys.RSAPublicKey

int_from_bytes = util.int_from_bytes
int_to_bytes = util.int_to_bytes
OrderedDict = util.OrderedDict
timezone = util.timezone

armor = pem.armor
unarmor = pem.unarmor

CertBag = pkcs12.CertBag
Pfx = pkcs12.Pfx
SafeContents = pkcs12.SafeContents

Certificate = x509.Certificate
TrustedCertificate = x509.TrustedCertificate

__all__ = [
    'armor',
    'CertBag',
    'Certificate',
    'DHParameters',
    'DSAParams',
    'DSAPrivateKey',
    'DSASignature',
    'ECDomainParameters',
    'ECPointBitString',
    'ECPrivateKey',
    'EncryptedData',
    'EncryptedPrivateKeyInfo',
    'int_from_bytes',
    'int_to_bytes',
    'Integer',
    'KeyExchangeAlgorithm',
    'Null',
    'OctetString',
    'OrderedDict',
    'Pbkdf2Salt',
    'Pfx',
    'PrivateKeyAlgorithm',
    'PrivateKeyInfo',
    'PublicKeyAlgorithm',
    'PublicKeyInfo',
    'RSAPrivateKey',
    'RSAPublicKey',
    'SafeContents',
    'timezone',
    'TrustedCertificate',
    'unarmor',
]
