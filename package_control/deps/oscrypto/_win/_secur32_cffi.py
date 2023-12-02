# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import sys

from .._ffi import register_ffi
from .._types import str_cls
from ..errors import LibraryNotFoundError

import cffi


__all__ = [
    'get_error',
    'secur32',
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
    typedef unsigned int ALG_ID;
    typedef WCHAR SEC_WCHAR;
    typedef unsigned long SECURITY_STATUS;
    typedef void *LUID;
    typedef void *SEC_GET_KEY_FN;

    typedef struct _SecHandle {
        ULONG_PTR dwLower;
        ULONG_PTR dwUpper;
    } SecHandle;
    typedef SecHandle CredHandle;
    typedef SecHandle CtxtHandle;

    typedef struct _SCHANNEL_CRED {
        DWORD dwVersion;
        DWORD cCreds;
        void *paCred;
        HCERTSTORE hRootStore;
        DWORD cMappers;
        void **aphMappers;
        DWORD cSupportedAlgs;
        ALG_ID *palgSupportedAlgs;
        DWORD grbitEnabledProtocols;
        DWORD dwMinimumCipherStrength;
        DWORD dwMaximumCipherStrength;
        DWORD dwSessionLifespan;
        DWORD dwFlags;
        DWORD dwCredFormat;
    } SCHANNEL_CRED;

    typedef struct _TimeStamp {
        DWORD dwLowDateTime;
        DWORD dwHighDateTime;
    } TimeStamp;

    typedef struct _SecBuffer {
        ULONG cbBuffer;
        ULONG BufferType;
        BYTE *pvBuffer;
    } SecBuffer;

    typedef struct _SecBufferDesc {
        ULONG ulVersion;
        ULONG cBuffers;
        SecBuffer *pBuffers;
    } SecBufferDesc;

    typedef struct _SecPkgContext_StreamSizes {
        ULONG cbHeader;
        ULONG cbTrailer;
        ULONG cbMaximumMessage;
        ULONG cBuffers;
        ULONG cbBlockSize;
    } SecPkgContext_StreamSizes;

    typedef struct _CERT_CONTEXT {
        DWORD dwCertEncodingType;
        BYTE *pbCertEncoded;
        DWORD cbCertEncoded;
        void *pCertInfo;
        HCERTSTORE hCertStore;
    } CERT_CONTEXT;

    typedef struct _SecPkgContext_ConnectionInfo {
        DWORD dwProtocol;
        ALG_ID aiCipher;
        DWORD dwCipherStrength;
        ALG_ID aiHash;
        DWORD dwHashStrength;
        ALG_ID aiExch;
        DWORD dwExchStrength;
    } SecPkgContext_ConnectionInfo;

    SECURITY_STATUS AcquireCredentialsHandleW(SEC_WCHAR *pszPrincipal, SEC_WCHAR *pszPackage, ULONG fCredentialUse,
                    LUID *pvLogonID, void *pAuthData, SEC_GET_KEY_FN pGetKeyFn, void *pvGetKeyArgument,
                    CredHandle *phCredential, TimeStamp *ptsExpiry);
    SECURITY_STATUS FreeCredentialsHandle(CredHandle *phCredential);
    SECURITY_STATUS InitializeSecurityContextW(CredHandle *phCredential, CtxtHandle *phContext,
                    SEC_WCHAR *pszTargetName, ULONG fContextReq, ULONG Reserved1, ULONG TargetDataRep,
                    SecBufferDesc *pInput, ULONG Reserved2, CtxtHandle *phNewContext, SecBufferDesc *pOutput,
                    ULONG *pfContextAttr, TimeStamp *ptsExpiry);
    SECURITY_STATUS FreeContextBuffer(void *pvContextBuffer);
    SECURITY_STATUS ApplyControlToken(CtxtHandle *phContext, SecBufferDesc *pInput);
    SECURITY_STATUS DeleteSecurityContext(CtxtHandle *phContext);
    SECURITY_STATUS QueryContextAttributesW(CtxtHandle *phContext, ULONG ulAttribute, void *pBuffer);
    SECURITY_STATUS EncryptMessage(CtxtHandle *phContext, ULONG fQOP, SecBufferDesc *pMessage, ULONG MessageSeqNo);
    SECURITY_STATUS DecryptMessage(CtxtHandle *phContext, SecBufferDesc *pMessage, ULONG MessageSeqNo, ULONG *pfQOP);
""")


try:
    secur32 = ffi.dlopen('secur32.dll')
    register_ffi(secur32, ffi)

except (OSError) as e:
    if str_cls(e).find('cannot load library') != -1:
        raise LibraryNotFoundError('secur32.dll could not be found')
    raise


def get_error():
    return ffi.getwinerror()
