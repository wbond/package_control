# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import sys

import ctypes
from ctypes import windll, wintypes, POINTER, c_void_p, c_uint, Structure
from ctypes.wintypes import DWORD, ULONG

from .._ffi import FFIEngineError
from .._types import str_cls
from ..errors import LibraryNotFoundError


__all__ = [
    'get_error',
    'secur32',
]


try:
    secur32 = windll.secur32
except (OSError) as e:
    if str_cls(e).find('The specified module could not be found') != -1:
        raise LibraryNotFoundError('secur32.dll could not be found')
    raise

HCERTSTORE = wintypes.HANDLE
ALG_ID = c_uint
if sys.maxsize > 2 ** 32:
    ULONG_PTR = ctypes.c_uint64
else:
    ULONG_PTR = ctypes.c_ulong
SEC_GET_KEY_FN = c_void_p
LUID = c_void_p
SECURITY_STATUS = ctypes.c_ulong
SEC_WCHAR = wintypes.WCHAR

try:
    class SecHandle(Structure):
        _fields_ = [
            ('dwLower', ULONG_PTR),
            ('dwUpper', ULONG_PTR),
        ]

    CredHandle = SecHandle
    CtxtHandle = SecHandle

    class SCHANNEL_CRED(Structure):  # noqa
        _fields_ = [
            ('dwVersion', DWORD),
            ('cCreds', DWORD),
            ('paCred', c_void_p),
            ('hRootStore', HCERTSTORE),
            ('cMappers', DWORD),
            ('aphMappers', POINTER(c_void_p)),
            ('cSupportedAlgs', DWORD),
            ('palgSupportedAlgs', POINTER(ALG_ID)),
            ('grbitEnabledProtocols', DWORD),
            ('dwMinimumCipherStrength', DWORD),
            ('dwMaximumCipherStrength', DWORD),
            ('dwSessionLifespan', DWORD),
            ('dwFlags', DWORD),
            ('dwCredFormat', DWORD),
        ]

    class TimeStamp(Structure):
        _fields_ = [
            ('dwLowDateTime', DWORD),
            ('dwHighDateTime', DWORD),
        ]

    class SecBuffer(Structure):
        _fields_ = [
            ('cbBuffer', ULONG),
            ('BufferType', ULONG),
            ('pvBuffer', POINTER(ctypes.c_byte)),
        ]

    PSecBuffer = POINTER(SecBuffer)

    class SecBufferDesc(Structure):
        _fields_ = [
            ('ulVersion', ULONG),
            ('cBuffers', ULONG),
            ('pBuffers', PSecBuffer),
        ]

    class SecPkgContext_StreamSizes(Structure):  # noqa
        _fields_ = [
            ('cbHeader', ULONG),
            ('cbTrailer', ULONG),
            ('cbMaximumMessage', ULONG),
            ('cBuffers', ULONG),
            ('cbBlockSize', ULONG),
        ]

    class SecPkgContext_ConnectionInfo(Structure):  # noqa
        _fields_ = [
            ('dwProtocol', DWORD),
            ('aiCipher', ALG_ID),
            ('dwCipherStrength', DWORD),
            ('aiHash', ALG_ID),
            ('dwHashStrength', DWORD),
            ('aiExch', ALG_ID),
            ('dwExchStrength', DWORD),
        ]

    secur32.AcquireCredentialsHandleW.argtypes = [
        POINTER(SEC_WCHAR),
        POINTER(SEC_WCHAR),
        ULONG,
        POINTER(LUID),
        c_void_p,
        SEC_GET_KEY_FN,
        c_void_p,
        POINTER(CredHandle),
        POINTER(TimeStamp)
    ]
    secur32.AcquireCredentialsHandleW.restype = SECURITY_STATUS

    secur32.FreeCredentialsHandle.argtypes = [
        POINTER(CredHandle)
    ]
    secur32.FreeCredentialsHandle.restype = SECURITY_STATUS

    secur32.InitializeSecurityContextW.argtypes = [
        POINTER(CredHandle),
        POINTER(CtxtHandle),
        POINTER(SEC_WCHAR),
        ULONG,
        ULONG,
        ULONG,
        POINTER(SecBufferDesc),
        ULONG,
        POINTER(CtxtHandle),
        POINTER(SecBufferDesc),
        POINTER(ULONG),
        POINTER(TimeStamp)
    ]
    secur32.InitializeSecurityContextW.restype = SECURITY_STATUS

    secur32.FreeContextBuffer.argtypes = [
        c_void_p
    ]
    secur32.FreeContextBuffer.restype = SECURITY_STATUS

    secur32.ApplyControlToken.argtypes = [
        POINTER(CtxtHandle),
        POINTER(SecBufferDesc)
    ]
    secur32.ApplyControlToken.restype = SECURITY_STATUS

    secur32.DeleteSecurityContext.argtypes = [
        POINTER(CtxtHandle)
    ]
    secur32.DeleteSecurityContext.restype = SECURITY_STATUS

    secur32.QueryContextAttributesW.argtypes = [
        POINTER(CtxtHandle),
        ULONG,
        c_void_p
    ]
    secur32.QueryContextAttributesW.restype = SECURITY_STATUS

    secur32.EncryptMessage.argtypes = [
        POINTER(CtxtHandle),
        ULONG,
        POINTER(SecBufferDesc),
        ULONG
    ]
    secur32.EncryptMessage.restype = SECURITY_STATUS

    secur32.DecryptMessage.argtypes = [
        POINTER(CtxtHandle),
        POINTER(SecBufferDesc),
        ULONG,
        POINTER(ULONG)
    ]
    secur32.DecryptMessage.restype = SECURITY_STATUS

except (AttributeError):
    raise FFIEngineError('Error initializing ctypes')


setattr(secur32, 'ALG_ID', ALG_ID)
setattr(secur32, 'CredHandle', CredHandle)
setattr(secur32, 'CtxtHandle', CtxtHandle)
setattr(secur32, 'SecBuffer', SecBuffer)
setattr(secur32, 'SecBufferDesc', SecBufferDesc)
setattr(secur32, 'SecPkgContext_StreamSizes', SecPkgContext_StreamSizes)
setattr(secur32, 'SecPkgContext_ConnectionInfo', SecPkgContext_ConnectionInfo)
setattr(secur32, 'SCHANNEL_CRED', SCHANNEL_CRED)


def get_error():
    error = ctypes.GetLastError()
    return (error, ctypes.FormatError(error))
