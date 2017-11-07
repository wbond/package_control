# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import sys

import ctypes
from ctypes import windll, wintypes, POINTER, Structure, c_void_p, c_char_p
from ctypes.wintypes import DWORD

from .._ffi import FFIEngineError
from .._types import str_cls
from ..errors import LibraryNotFoundError
from ._kernel32 import kernel32


__all__ = [
    'crypt32',
    'get_error',
]


try:
    crypt32 = windll.crypt32
except (OSError) as e:
    if str_cls(e).find('The specified module could not be found') != -1:
        raise LibraryNotFoundError('crypt32.dll could not be found')
    raise

HCERTSTORE = wintypes.HANDLE
HCERTCHAINENGINE = wintypes.HANDLE
HCRYPTPROV = wintypes.HANDLE
HCRYPTKEY = wintypes.HANDLE
PBYTE = c_char_p
if sys.maxsize > 2 ** 32:
    ULONG_PTR = ctypes.c_uint64
else:
    ULONG_PTR = ctypes.c_ulong

try:
    class CRYPTOAPI_BLOB(Structure):  # noqa
        _fields_ = [
            ("cbData", DWORD),
            ("pbData", c_void_p),
        ]
    CRYPT_INTEGER_BLOB = CRYPTOAPI_BLOB
    CERT_NAME_BLOB = CRYPTOAPI_BLOB
    CRYPT_BIT_BLOB = CRYPTOAPI_BLOB
    CRYPT_OBJID_BLOB = CRYPTOAPI_BLOB

    class CRYPT_ALGORITHM_IDENTIFIER(Structure):  # noqa
        _fields_ = [
            ("pszObjId", wintypes.LPSTR),
            ("Parameters", CRYPT_OBJID_BLOB),
        ]

    class CERT_PUBLIC_KEY_INFO(Structure):  # noqa
        _fields_ = [
            ("Algorithm", CRYPT_ALGORITHM_IDENTIFIER),
            ("PublicKey", CRYPT_BIT_BLOB),
        ]

    class CERT_EXTENSION(Structure):  # noqa
        _fields_ = [
            ("pszObjId", wintypes.LPSTR),
            ("fCritical", wintypes.BOOL),
            ("Value", CRYPT_OBJID_BLOB),
        ]
    PCERT_EXTENSION = POINTER(CERT_EXTENSION)

    class CERT_INFO(Structure):  # noqa
        _fields_ = [
            ("dwVersion", DWORD),
            ("SerialNumber", CRYPT_INTEGER_BLOB),
            ("SignatureAlgorithm", CRYPT_ALGORITHM_IDENTIFIER),
            ("Issuer", CERT_NAME_BLOB),
            ("NotBefore", kernel32.FILETIME),
            ("NotAfter", kernel32.FILETIME),
            ("Subject", CERT_NAME_BLOB),
            ("SubjectPublicKeyInfo", CERT_PUBLIC_KEY_INFO),
            ("IssuerUniqueId", CRYPT_BIT_BLOB),
            ("SubjectUniqueId", CRYPT_BIT_BLOB),
            ("cExtension", DWORD),
            ("rgExtension", POINTER(PCERT_EXTENSION)),
        ]
    PCERT_INFO = POINTER(CERT_INFO)

    class CERT_CONTEXT(Structure):  # noqa
        _fields_ = [
            ("dwCertEncodingType", DWORD),
            ("pbCertEncoded", c_void_p),
            ("cbCertEncoded", DWORD),
            ("pCertInfo", PCERT_INFO),
            ("hCertStore", HCERTSTORE)
        ]

    PCERT_CONTEXT = POINTER(CERT_CONTEXT)

    class CERT_ENHKEY_USAGE(Structure):  # noqa
        _fields_ = [
            ('cUsageIdentifier', DWORD),
            ('rgpszUsageIdentifier', POINTER(POINTER(wintypes.BYTE))),
        ]

    PCERT_ENHKEY_USAGE = POINTER(CERT_ENHKEY_USAGE)

    class CERT_TRUST_STATUS(Structure):  # noqa
        _fields_ = [
            ('dwErrorStatus', DWORD),
            ('dwInfoStatus', DWORD),
        ]

    class CERT_CHAIN_ELEMENT(Structure):  # noqa
        _fields_ = [
            ('cbSize', DWORD),
            ('pCertContext', PCERT_CONTEXT),
            ('TrustStatus', CERT_TRUST_STATUS),
            ('pRevocationInfo', c_void_p),
            ('pIssuanceUsage', PCERT_ENHKEY_USAGE),
            ('pApplicationUsage', PCERT_ENHKEY_USAGE),
            ('pwszExtendedErrorInfo', wintypes.LPCWSTR),
        ]

    PCERT_CHAIN_ELEMENT = POINTER(CERT_CHAIN_ELEMENT)

    class CERT_SIMPLE_CHAIN(Structure):  # noqa
        _fields_ = [
            ('cbSize', DWORD),
            ('TrustStatus', CERT_TRUST_STATUS),
            ('cElement', DWORD),
            ('rgpElement', POINTER(PCERT_CHAIN_ELEMENT)),
            ('pTrustListInfo', c_void_p),
            ('fHasRevocationFreshnessTime', wintypes.BOOL),
            ('dwRevocationFreshnessTime', DWORD),
        ]

    PCERT_SIMPLE_CHAIN = POINTER(CERT_SIMPLE_CHAIN)

    class CERT_CHAIN_CONTEXT(Structure):  # noqa
        _fields_ = [
            ('cbSize', DWORD),
            ('TrustStatus', CERT_TRUST_STATUS),
            ('cChain', DWORD),
            ('rgpChain', POINTER(PCERT_SIMPLE_CHAIN)),
            ('cLowerQualityChainContext', DWORD),
            ('rgpLowerQualityChainContext', c_void_p),
            ('fHasRevocationFreshnessTime', wintypes.BOOL),
            ('dwRevocationFreshnessTime', DWORD),
        ]

    PCERT_CHAIN_CONTEXT = POINTER(CERT_CHAIN_CONTEXT)

    class CERT_USAGE_MATCH(Structure):  # noqa
        _fields_ = [
            ('dwType', DWORD),
            ('Usage', CERT_ENHKEY_USAGE),
        ]

    class CERT_CHAIN_PARA(Structure):  # noqa
        _fields_ = [
            ('cbSize', DWORD),
            ('RequestedUsage', CERT_USAGE_MATCH),
        ]

    class CERT_CHAIN_POLICY_PARA(Structure):  # noqa
        _fields_ = [
            ('cbSize', DWORD),
            ('dwFlags', DWORD),
            ('pvExtraPolicyPara', c_void_p),
        ]

    class SSL_EXTRA_CERT_CHAIN_POLICY_PARA(Structure):  # noqa
        _fields_ = [
            ('cbSize', DWORD),
            ('dwAuthType', DWORD),
            ('fdwChecks', DWORD),
            ('pwszServerName', wintypes.LPCWSTR),
        ]

    class CERT_CHAIN_POLICY_STATUS(Structure):  # noqa
        _fields_ = [
            ('cbSize', DWORD),
            ('dwError', DWORD),
            ('lChainIndex', wintypes.LONG),
            ('lElementIndex', wintypes.LONG),
            ('pvExtraPolicyStatus', c_void_p),
        ]

    crypt32.CertOpenStore.argtypes = [
        wintypes.LPCSTR,
        DWORD,
        HCRYPTPROV,
        DWORD,
        c_void_p
    ]
    crypt32.CertOpenStore.restype = HCERTSTORE

    crypt32.CertAddEncodedCertificateToStore.argtypes = [
        HCERTSTORE,
        DWORD,
        PBYTE,
        DWORD,
        DWORD,
        POINTER(PCERT_CONTEXT)
    ]
    crypt32.CertAddEncodedCertificateToStore.restype = wintypes.BOOL

    crypt32.CertGetCertificateChain.argtypes = [
        HCERTCHAINENGINE,
        PCERT_CONTEXT,
        POINTER(kernel32.FILETIME),
        HCERTSTORE,
        POINTER(CERT_CHAIN_PARA),
        DWORD,
        c_void_p,
        POINTER(PCERT_CHAIN_CONTEXT)
    ]
    crypt32.CertGetCertificateChain.restype = wintypes.BOOL

    crypt32.CertVerifyCertificateChainPolicy.argtypes = [
        ULONG_PTR,
        PCERT_CHAIN_CONTEXT,
        POINTER(CERT_CHAIN_POLICY_PARA),
        POINTER(CERT_CHAIN_POLICY_STATUS)
    ]
    crypt32.CertVerifyCertificateChainPolicy.restype = wintypes.BOOL

    crypt32.CertFreeCertificateChain.argtypes = [
        PCERT_CHAIN_CONTEXT
    ]
    crypt32.CertFreeCertificateChain.restype = None

    crypt32.CertOpenSystemStoreW.argtypes = [
        wintypes.HANDLE,
        wintypes.LPCWSTR
    ]
    crypt32.CertOpenSystemStoreW.restype = HCERTSTORE

    crypt32.CertEnumCertificatesInStore.argtypes = [
        HCERTSTORE,
        PCERT_CONTEXT
    ]
    crypt32.CertEnumCertificatesInStore.restype = PCERT_CONTEXT

    crypt32.CertCloseStore.argtypes = [
        HCERTSTORE,
        DWORD
    ]
    crypt32.CertCloseStore.restype = wintypes.BOOL

    crypt32.CertGetEnhancedKeyUsage.argtypes = [
        PCERT_CONTEXT,
        DWORD,
        c_void_p,
        POINTER(DWORD)
    ]
    crypt32.CertGetEnhancedKeyUsage.restype = wintypes.BOOL

except (AttributeError):
    raise FFIEngineError('Error initializing ctypes')


setattr(crypt32, 'FILETIME', kernel32.FILETIME)
setattr(crypt32, 'CERT_ENHKEY_USAGE', CERT_ENHKEY_USAGE)
setattr(crypt32, 'CERT_CONTEXT', CERT_CONTEXT)
setattr(crypt32, 'PCERT_CONTEXT', PCERT_CONTEXT)
setattr(crypt32, 'CERT_USAGE_MATCH', CERT_USAGE_MATCH)
setattr(crypt32, 'CERT_CHAIN_PARA', CERT_CHAIN_PARA)
setattr(crypt32, 'CERT_CHAIN_POLICY_PARA', CERT_CHAIN_POLICY_PARA)
setattr(crypt32, 'SSL_EXTRA_CERT_CHAIN_POLICY_PARA', SSL_EXTRA_CERT_CHAIN_POLICY_PARA)
setattr(crypt32, 'CERT_CHAIN_POLICY_STATUS', CERT_CHAIN_POLICY_STATUS)
setattr(crypt32, 'PCERT_CHAIN_CONTEXT', PCERT_CHAIN_CONTEXT)


def get_error():
    error = ctypes.GetLastError()
    return (error, ctypes.FormatError(error))
