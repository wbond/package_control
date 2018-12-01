# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import ctypes
from ctypes import windll, wintypes, POINTER, Structure, c_void_p, c_char_p, c_uint
from ctypes.wintypes import BOOL, DWORD

from .._ffi import FFIEngineError
from .._types import str_cls
from ..errors import LibraryNotFoundError


__all__ = [
    'advapi32',
    'get_error',
]


try:
    advapi32 = windll.advapi32
except (OSError) as e:
    if str_cls(e).find('The specified module could not be found') != -1:
        raise LibraryNotFoundError('advapi32.dll could not be found')
    raise

HCRYPTPROV = wintypes.HANDLE
HCRYPTKEY = wintypes.HANDLE
HCRYPTHASH = wintypes.HANDLE
PBYTE = c_char_p
ALG_ID = c_uint

try:
    class CRYPTOAPI_BLOB(Structure):  # noqa
        _fields_ = [
            ("cbData", DWORD),
            ("pbData", POINTER(ctypes.c_byte)),
        ]
    CRYPT_INTEGER_BLOB = CRYPTOAPI_BLOB
    CRYPT_OBJID_BLOB = CRYPTOAPI_BLOB
    CRYPT_DER_BLOB = CRYPTOAPI_BLOB
    CRYPT_ATTR_BLOB = CRYPTOAPI_BLOB

    class CRYPT_ALGORITHM_IDENTIFIER(Structure):
        _fields = [
            ('pszObjId', wintypes.LPSTR),
            ('Parameters', CRYPT_OBJID_BLOB),
        ]

    class CRYPT_BIT_BLOB(Structure):
        _fields_ = [
            ('cbData', DWORD),
            ('pbData', PBYTE),
            ('cUnusedBits', DWORD),
        ]

    class CERT_PUBLIC_KEY_INFO(Structure):
        _fields_ = [
            ('Algorithm', CRYPT_ALGORITHM_IDENTIFIER),
            ('PublicKey', CRYPT_BIT_BLOB),
        ]

    class CRYPT_ATTRIBUTE(Structure):
        _fields_ = [
            ('pszObjId', wintypes.LPSTR),
            ('cValue', DWORD),
            ('rgValue', POINTER(CRYPT_ATTR_BLOB)),
        ]

    class CRYPT_ATTRIBUTES(Structure):
        _fields_ = [
            ('cAttr', DWORD),
            ('rgAttr', POINTER(CRYPT_ATTRIBUTE)),
        ]

    class CRYPT_PRIVATE_KEY_INFO(Structure):
        _fields_ = [
            ('Version', DWORD),
            ('Algorithm', CRYPT_ALGORITHM_IDENTIFIER),
            ('PrivateKey', CRYPT_DER_BLOB),
            ('pAttributes', POINTER(CRYPT_ATTRIBUTES)),
        ]

    class PUBLICKEYSTRUC(Structure):
        _fields_ = [
            ('bType', wintypes.BYTE),
            ('bVersion', wintypes.BYTE),
            ('reserved', wintypes.WORD),
            ('aiKeyAlg', ALG_ID),
        ]
    BLOBHEADER = PUBLICKEYSTRUC

    class DSSPUBKEY(Structure):
        _fields_ = [
            ('magic', DWORD),
            ('bitlen', DWORD),
        ]

    class DSSBLOBHEADER(Structure):
        _fields_ = [
            ('publickeystruc', PUBLICKEYSTRUC),
            ('dsspubkey', DSSPUBKEY),
        ]

    class RSAPUBKEY(Structure):
        _fields_ = [
            ('magic', DWORD),
            ('bitlen', DWORD),
            ('pubexp', DWORD),
        ]

    class RSABLOBHEADER(Structure):
        _fields_ = [
            ('publickeystruc', PUBLICKEYSTRUC),
            ('rsapubkey', RSAPUBKEY),
        ]

    class PLAINTEXTKEYBLOB(Structure):
        _fields_ = [
            ('hdr', BLOBHEADER),
            ('dwKeySize', DWORD),
            # rgbKeyData omitted since it is a flexible array member
        ]

    class DSSSEED(Structure):
        _fields_ = [
            ('counter', DWORD),
            ('seed', wintypes.BYTE * 20),
        ]

    advapi32.CryptAcquireContextW.argtypes = [
        POINTER(HCRYPTPROV),
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        DWORD,
        DWORD
    ]
    advapi32.CryptAcquireContextW.restype = wintypes.BOOL

    advapi32.CryptReleaseContext.argtypes = [
        HCRYPTPROV,
        DWORD
    ]
    advapi32.CryptReleaseContext.restype = wintypes.BOOL

    advapi32.CryptImportKey.argtypes = [
        HCRYPTPROV,
        PBYTE,
        DWORD,
        HCRYPTKEY,
        DWORD,
        POINTER(HCRYPTKEY)
    ]
    advapi32.CryptImportKey.restype = BOOL

    advapi32.CryptGenKey.argtypes = [
        HCRYPTPROV,
        ALG_ID,
        DWORD,
        POINTER(HCRYPTKEY)
    ]
    advapi32.CryptGenKey.restype = wintypes.BOOL

    advapi32.CryptGetKeyParam.argtypes = [
        HCRYPTKEY,
        DWORD,
        PBYTE,
        POINTER(DWORD),
        DWORD
    ]
    advapi32.CryptGetKeyParam.restype = wintypes.BOOL

    advapi32.CryptSetKeyParam.argtypes = [
        HCRYPTKEY,
        DWORD,
        c_void_p,
        DWORD
    ]
    advapi32.CryptSetKeyParam.restype = wintypes.BOOL

    advapi32.CryptExportKey.argtypes = [
        HCRYPTKEY,
        HCRYPTKEY,
        DWORD,
        DWORD,
        PBYTE,
        POINTER(DWORD)
    ]
    advapi32.CryptExportKey.restype = BOOL

    advapi32.CryptDestroyKey.argtypes = [
        HCRYPTKEY
    ]
    advapi32.CryptDestroyKey.restype = wintypes.BOOL

    advapi32.CryptCreateHash.argtypes = [
        HCRYPTPROV,
        ALG_ID,
        HCRYPTKEY,
        DWORD,
        POINTER(HCRYPTHASH)
    ]
    advapi32.CryptCreateHash.restype = BOOL

    advapi32.CryptHashData.argtypes = [
        HCRYPTHASH,
        PBYTE,
        DWORD,
        DWORD
    ]
    advapi32.CryptHashData.restype = BOOL

    advapi32.CryptSetHashParam.argtypes = [
        HCRYPTHASH,
        DWORD,
        PBYTE,
        DWORD
    ]
    advapi32.CryptSetHashParam.restype = BOOL

    advapi32.CryptSignHashW.argtypes = [
        HCRYPTHASH,
        DWORD,
        wintypes.LPCWSTR,
        DWORD,
        PBYTE,
        POINTER(DWORD)
    ]
    advapi32.CryptSignHashW.restype = BOOL

    advapi32.CryptVerifySignatureW.argtypes = [
        HCRYPTHASH,
        PBYTE,
        DWORD,
        HCRYPTKEY,
        wintypes.LPCWSTR,
        DWORD
    ]
    advapi32.CryptVerifySignatureW.restype = BOOL

    advapi32.CryptDestroyHash.argtypes = [
        HCRYPTHASH
    ]
    advapi32.CryptDestroyHash.restype = wintypes.BOOL

    advapi32.CryptEncrypt.argtypes = [
        HCRYPTKEY,
        HCRYPTHASH,
        BOOL,
        DWORD,
        PBYTE,
        POINTER(DWORD),
        DWORD
    ]
    advapi32.CryptEncrypt.restype = BOOL

    advapi32.CryptDecrypt.argtypes = [
        HCRYPTKEY,
        HCRYPTHASH,
        BOOL,
        DWORD,
        PBYTE,
        POINTER(DWORD)
    ]
    advapi32.CryptDecrypt.restype = BOOL

except (AttributeError):
    raise FFIEngineError('Error initializing ctypes')


setattr(advapi32, 'HCRYPTPROV', HCRYPTPROV)
setattr(advapi32, 'HCRYPTKEY', HCRYPTKEY)
setattr(advapi32, 'HCRYPTHASH', HCRYPTHASH)
setattr(advapi32, 'CRYPT_INTEGER_BLOB', CRYPT_INTEGER_BLOB)
setattr(advapi32, 'CRYPT_OBJID_BLOB', CRYPT_OBJID_BLOB)
setattr(advapi32, 'CRYPT_DER_BLOB', CRYPT_DER_BLOB)
setattr(advapi32, 'CRYPT_ATTR_BLOB', CRYPT_ATTR_BLOB)
setattr(advapi32, 'CRYPT_ALGORITHM_IDENTIFIER', CRYPT_ALGORITHM_IDENTIFIER)
setattr(advapi32, 'CRYPT_BIT_BLOB', CRYPT_BIT_BLOB)
setattr(advapi32, 'CERT_PUBLIC_KEY_INFO', CERT_PUBLIC_KEY_INFO)
setattr(advapi32, 'CRYPT_PRIVATE_KEY_INFO', CRYPT_PRIVATE_KEY_INFO)
setattr(advapi32, 'CRYPT_ATTRIBUTE', CRYPT_ATTRIBUTE)
setattr(advapi32, 'CRYPT_ATTRIBUTES', CRYPT_ATTRIBUTES)
setattr(advapi32, 'PUBLICKEYSTRUC', PUBLICKEYSTRUC)
setattr(advapi32, 'DSSPUBKEY', DSSPUBKEY)
setattr(advapi32, 'DSSBLOBHEADER', DSSBLOBHEADER)
setattr(advapi32, 'RSAPUBKEY', RSAPUBKEY)
setattr(advapi32, 'RSABLOBHEADER', RSABLOBHEADER)
setattr(advapi32, 'BLOBHEADER', BLOBHEADER)
setattr(advapi32, 'PLAINTEXTKEYBLOB', PLAINTEXTKEYBLOB)
setattr(advapi32, 'DSSSEED', DSSSEED)


def get_error():
    error = ctypes.GetLastError()
    return (error, ctypes.FormatError(error))
