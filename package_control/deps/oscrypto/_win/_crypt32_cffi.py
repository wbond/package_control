# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import sys

from .._ffi import register_ffi
from .._types import str_cls
from ..errors import LibraryNotFoundError

import cffi


__all__ = [
    'crypt32',
    'get_error',
]


ffi = cffi.FFI()
if cffi.__version_info__ >= (0, 9):
    ffi.set_unicode(True)
if sys.maxsize > 2 ** 32:
    ffi.cdef("typedef uint64_t ULONG_PTR;")
else:
    ffi.cdef("typedef unsigned long ULONG_PTR;")
ffi.cdef("""
    typedef HANDLE HCERTSTORE;
    typedef unsigned char *PBYTE;


    typedef struct _CRYPTOAPI_BLOB {
        DWORD cbData;
        PBYTE pbData;
    } CRYPTOAPI_BLOB;
    typedef CRYPTOAPI_BLOB CRYPT_INTEGER_BLOB;
    typedef CRYPTOAPI_BLOB CERT_NAME_BLOB;
    typedef CRYPTOAPI_BLOB CRYPT_BIT_BLOB;
    typedef CRYPTOAPI_BLOB CRYPT_OBJID_BLOB;

    typedef struct _CRYPT_ALGORITHM_IDENTIFIER {
        LPSTR pszObjId;
        CRYPT_OBJID_BLOB Parameters;
    } CRYPT_ALGORITHM_IDENTIFIER;

    typedef struct _FILETIME {
        DWORD dwLowDateTime;
        DWORD dwHighDateTime;
    } FILETIME;

    typedef struct _CERT_PUBLIC_KEY_INFO {
        CRYPT_ALGORITHM_IDENTIFIER Algorithm;
        CRYPT_BIT_BLOB PublicKey;
    } CERT_PUBLIC_KEY_INFO;

    typedef struct _CERT_EXTENSION {
        LPSTR pszObjId;
        BOOL fCritical;
        CRYPT_OBJID_BLOB Value;
    } CERT_EXTENSION, *PCERT_EXTENSION;

    typedef struct _CERT_INFO {
        DWORD dwVersion;
        CRYPT_INTEGER_BLOB SerialNumber;
        CRYPT_ALGORITHM_IDENTIFIER SignatureAlgorithm;
        CERT_NAME_BLOB Issuer;
        FILETIME NotBefore;
        FILETIME NotAfter;
        CERT_NAME_BLOB Subject;
        CERT_PUBLIC_KEY_INFO SubjectPublicKeyInfo;
        CRYPT_BIT_BLOB IssuerUniqueId;
        CRYPT_BIT_BLOB SubjectUniqueId;
        DWORD cExtension;
        PCERT_EXTENSION *rgExtension;
    } CERT_INFO, *PCERT_INFO;

    typedef struct _CERT_CONTEXT {
        DWORD dwCertEncodingType;
        PBYTE pbCertEncoded;
        DWORD cbCertEncoded;
        PCERT_INFO pCertInfo;
        HCERTSTORE hCertStore;
    } CERT_CONTEXT, *PCERT_CONTEXT;

    typedef struct _CERT_TRUST_STATUS {
        DWORD dwErrorStatus;
        DWORD dwInfoStatus;
    } CERT_TRUST_STATUS, *PCERT_TRUST_STATUS;

    typedef struct _CERT_ENHKEY_USAGE {
        DWORD cUsageIdentifier;
        LPSTR *rgpszUsageIdentifier;
    } CERT_ENHKEY_USAGE, *PCERT_ENHKEY_USAGE;

    typedef struct _CERT_CHAIN_ELEMENT {
        DWORD cbSize;
        PCERT_CONTEXT pCertContext;
        CERT_TRUST_STATUS TrustStatus;
        void *pRevocationInfo;
        PCERT_ENHKEY_USAGE pIssuanceUsage;
        PCERT_ENHKEY_USAGE pApplicationUsage;
        LPCWSTR pwszExtendedErrorInfo;
    } CERT_CHAIN_ELEMENT, *PCERT_CHAIN_ELEMENT;

    typedef struct _CERT_SIMPLE_CHAIN {
        DWORD cbSize;
        CERT_TRUST_STATUS TrustStatus;
        DWORD cElement;
        PCERT_CHAIN_ELEMENT *rgpElement;
        void *pTrustListInfo;
        BOOL fHasRevocationFreshnessTime;
        DWORD dwRevocationFreshnessTime;
    } CERT_SIMPLE_CHAIN, *PCERT_SIMPLE_CHAIN;

    typedef struct _CERT_CHAIN_CONTEXT {
        DWORD cbSize;
        CERT_TRUST_STATUS TrustStatus;
        DWORD cChain;
        PCERT_SIMPLE_CHAIN *rgpChain;
        DWORD cLowerQualityChainContext;
        void *rgpLowerQualityChainContext;
        BOOL fHasRevocationFreshnessTime;
        DWORD dwRevocationFreshnessTime;
    } CERT_CHAIN_CONTEXT, *PCERT_CHAIN_CONTEXT;

    typedef struct _CERT_USAGE_MATCH {
        DWORD dwType;
        CERT_ENHKEY_USAGE Usage;
    } CERT_USAGE_MATCH;

    typedef struct _CERT_CHAIN_PARA {
        DWORD cbSize;
        CERT_USAGE_MATCH RequestedUsage;
    } CERT_CHAIN_PARA;

    typedef struct _CERT_CHAIN_POLICY_PARA {
        DWORD cbSize;
        DWORD dwFlags;
        void  *pvExtraPolicyPara;
    } CERT_CHAIN_POLICY_PARA;

    typedef struct _HTTPSPolicyCallbackData {
        DWORD cbSize;
        DWORD dwAuthType;
        DWORD fdwChecks;
        WCHAR *pwszServerName;
    } SSL_EXTRA_CERT_CHAIN_POLICY_PARA;

    typedef struct _CERT_CHAIN_POLICY_STATUS {
        DWORD cbSize;
        DWORD dwError;
        LONG lChainIndex;
        LONG lElementIndex;
        void *pvExtraPolicyStatus;
    } CERT_CHAIN_POLICY_STATUS;

    typedef HANDLE HCERTCHAINENGINE;
    typedef HANDLE HCRYPTPROV;

    HCERTSTORE CertOpenStore(LPCSTR lpszStoreProvider, DWORD dwMsgAndCertEncodingType, HCRYPTPROV hCryptProv,
                    DWORD dwFlags, void *pvPara);
    BOOL CertAddEncodedCertificateToStore(HCERTSTORE hCertStore, DWORD dwCertEncodingType, BYTE *pbCertEncoded,
                    DWORD cbCertEncoded, DWORD dwAddDisposition, PCERT_CONTEXT *ppCertContext);
    BOOL CertGetCertificateChain(HCERTCHAINENGINE hChainEngine, CERT_CONTEXT *pCertContext, FILETIME *pTime,
                    HCERTSTORE hAdditionalStore, CERT_CHAIN_PARA *pChainPara, DWORD dwFlags, void *pvReserved,
                    PCERT_CHAIN_CONTEXT *ppChainContext);
    BOOL CertVerifyCertificateChainPolicy(ULONG_PTR pszPolicyOID, PCERT_CHAIN_CONTEXT pChainContext,
                    CERT_CHAIN_POLICY_PARA *pPolicyPara, CERT_CHAIN_POLICY_STATUS *pPolicyStatus);
    void CertFreeCertificateChain(PCERT_CHAIN_CONTEXT pChainContext);

    HCERTSTORE CertOpenSystemStoreW(HANDLE hprov, LPCWSTR szSubsystemProtocol);
    PCERT_CONTEXT CertEnumCertificatesInStore(HCERTSTORE hCertStore, CERT_CONTEXT *pPrevCertContext);
    BOOL CertCloseStore(HCERTSTORE hCertStore, DWORD dwFlags);
    BOOL CertGetEnhancedKeyUsage(CERT_CONTEXT *pCertContext, DWORD dwFlags, CERT_ENHKEY_USAGE *pUsage, DWORD *pcbUsage);
""")


try:
    crypt32 = ffi.dlopen('crypt32.dll')
    register_ffi(crypt32, ffi)

except (OSError) as e:
    if str_cls(e).find('cannot load library') != -1:
        raise LibraryNotFoundError('crypt32.dll could not be found')
    raise


def get_error():
    return ffi.getwinerror()
