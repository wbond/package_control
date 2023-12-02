# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from .._ffi import register_ffi
from .._types import str_cls
from ..errors import LibraryNotFoundError

import cffi


__all__ = [
    'advapi32',
    'get_error',
]


ffi = cffi.FFI()
if cffi.__version_info__ >= (0, 9):
    ffi.set_unicode(True)
ffi.cdef("""
    typedef HANDLE HCRYPTPROV;
    typedef HANDLE HCRYPTKEY;
    typedef HANDLE HCRYPTHASH;
    typedef unsigned int ALG_ID;

    typedef struct _CRYPTOAPI_BLOB {
        DWORD cbData;
        BYTE  *pbData;
    } CRYPT_INTEGER_BLOB, CRYPT_OBJID_BLOB, CRYPT_DER_BLOB, CRYPT_ATTR_BLOB;

    typedef struct _CRYPT_ALGORITHM_IDENTIFIER {
        LPSTR            pszObjId;
        CRYPT_OBJID_BLOB Parameters;
    } CRYPT_ALGORITHM_IDENTIFIER;

    typedef struct _CRYPT_BIT_BLOB {
        DWORD cbData;
        BYTE  *pbData;
        DWORD cUnusedBits;
    } CRYPT_BIT_BLOB;

    typedef struct _CERT_PUBLIC_KEY_INFO {
        CRYPT_ALGORITHM_IDENTIFIER Algorithm;
        CRYPT_BIT_BLOB             PublicKey;
    } CERT_PUBLIC_KEY_INFO;

    typedef struct _CRYPT_ATTRIBUTE {
        LPSTR           pszObjId;
        DWORD           cValue;
        CRYPT_ATTR_BLOB *rgValue;
    } CRYPT_ATTRIBUTE;

    typedef struct _CRYPT_ATTRIBUTES {
        DWORD           cAttr;
        CRYPT_ATTRIBUTE *rgAttr;
    } CRYPT_ATTRIBUTES;

    typedef struct _CRYPT_PRIVATE_KEY_INFO {
        DWORD                      Version;
        CRYPT_ALGORITHM_IDENTIFIER Algorithm;
        CRYPT_DER_BLOB             PrivateKey;
        CRYPT_ATTRIBUTES           *pAttributes;
    } CRYPT_PRIVATE_KEY_INFO;

    typedef struct _PUBLICKEYSTRUC {
        BYTE   bType;
        BYTE   bVersion;
        WORD   reserved;
        ALG_ID aiKeyAlg;
    } BLOBHEADER, PUBLICKEYSTRUC;

    typedef struct _DSSPUBKEY {
        DWORD magic;
        DWORD bitlen;
    } DSSPUBKEY;

    typedef struct _DSSBLOBHEADER {
        PUBLICKEYSTRUC  publickeystruc;
        DSSPUBKEY dsspubkey;
    } DSSBLOBHEADER;

    typedef struct _RSAPUBKEY {
        DWORD magic;
        DWORD bitlen;
        DWORD pubexp;
    } RSAPUBKEY;

    typedef struct _RSABLOBHEADER {
        PUBLICKEYSTRUC  publickeystruc;
        RSAPUBKEY rsapubkey;
    } RSABLOBHEADER;

    typedef struct _PLAINTEXTKEYBLOB {
        BLOBHEADER hdr;
        DWORD      dwKeySize;
        // rgbKeyData omitted since it is a flexible array member
    } PLAINTEXTKEYBLOB;

    typedef struct _DSSSEED {
        DWORD counter;
        BYTE  seed[20];
    } DSSSEED;

    BOOL CryptAcquireContextW(HCRYPTPROV *phProv, LPCWSTR pszContainer, LPCWSTR pszProvider,
                DWORD dwProvType, DWORD dwFlags);
    BOOL CryptReleaseContext(HCRYPTPROV hProv, DWORD dwFlags);

    BOOL CryptImportKey(HCRYPTPROV hProv, BYTE *pbData, DWORD dwDataLen,
                HCRYPTKEY hPubKey, DWORD dwFlags, HCRYPTKEY *phKey);
    BOOL CryptGenKey(HCRYPTPROV hProv, ALG_ID Algid, DWORD dwFlags, HCRYPTKEY *phKey);
    BOOL CryptGetKeyParam(HCRYPTKEY hKey, DWORD dwParam, BYTE *pbData, DWORD *pdwDataLen, DWORD dwFlags);
    BOOL CryptSetKeyParam(HCRYPTKEY hKey, DWORD dwParam, void *pbData, DWORD dwFlags);
    BOOL CryptExportKey(HCRYPTKEY hKey, HCRYPTKEY hExpKey, DWORD dwBlobType,
                DWORD dwFlags, BYTE *pbData, DWORD *pdwDataLen);
    BOOL CryptDestroyKey(HCRYPTKEY hKey);

    BOOL CryptCreateHash(HCRYPTPROV hProv, ALG_ID Algid, HCRYPTKEY hKey,
                DWORD dwFlags, HCRYPTHASH *phHash);
    BOOL CryptHashData(HCRYPTHASH hHash, BYTE *pbData, DWORD dwDataLen, DWORD dwFlags);
    BOOL CryptSetHashParam(HCRYPTHASH hHash, DWORD dwParam, BYTE *pbData, DWORD dwFlags);
    BOOL CryptSignHashW(HCRYPTHASH hHash, DWORD dwKeySpec, LPCWSTR sDescription,
                DWORD dwFlags, BYTE *pbSignature, DWORD *pdwSigLen);
    BOOL CryptVerifySignatureW(HCRYPTHASH hHash, BYTE *pbSignature, DWORD dwSigLen,
                HCRYPTKEY hPubKey, LPCWSTR sDescription, DWORD dwFlags);
    BOOL CryptDestroyHash(HCRYPTHASH hHash);

    BOOL CryptEncrypt(HCRYPTKEY hKey, HCRYPTHASH hHash, BOOL Final, DWORD dwFlags,
                BYTE *pbData, DWORD *pdwDataLen, DWORD dwBufLen);
    BOOL CryptDecrypt(HCRYPTKEY hKey, HCRYPTHASH hHash, BOOL Final, DWORD dwFlags,
                BYTE *pbData, DWORD *pdwDataLen);
""")


try:
    advapi32 = ffi.dlopen('advapi32.dll')
    register_ffi(advapi32, ffi)

except (OSError) as e:
    if str_cls(e).find('cannot load library') != -1:
        raise LibraryNotFoundError('advapi32.dll could not be found')
    raise


def get_error():
    return ffi.getwinerror()
