# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import platform
from ctypes.util import find_library
from ctypes import c_void_p, c_int32, c_char_p, c_size_t, c_byte, c_int, c_uint32, c_uint64, c_ulong, c_long, c_bool
from ctypes import CDLL, POINTER, CFUNCTYPE, Structure

from .._ffi import FFIEngineError
from ..errors import LibraryNotFoundError


__all__ = [
    'Security',
    'version',
    'version_info',
]


version = platform.mac_ver()[0]
version_info = tuple(map(int, version.split('.')))

if version_info < (10, 7):
    raise OSError('Only OS X 10.7 and newer are supported, not %s.%s' % (version_info[0], version_info[1]))

security_path = find_library('Security')
if not security_path:
    raise LibraryNotFoundError('The library Security could not be found')

Security = CDLL(security_path, use_errno=True)

Boolean = c_bool
CFIndex = c_long
CFData = c_void_p
CFString = c_void_p
CFArray = c_void_p
CFDictionary = c_void_p
CFError = c_void_p
CFType = c_void_p
CFTypeID = c_ulong

CFTypeRef = POINTER(CFType)
CFAllocatorRef = c_void_p

OSStatus = c_int32

CFDataRef = POINTER(CFData)
CFStringRef = POINTER(CFString)
CFArrayRef = POINTER(CFArray)
CFDictionaryRef = POINTER(CFDictionary)
CFErrorRef = POINTER(CFError)

SecKeyRef = POINTER(c_void_p)
SecCertificateRef = POINTER(c_void_p)
SecTransformRef = POINTER(c_void_p)
SecRandomRef = c_void_p
SecTrustSettingsDomain = c_uint32
SecItemImportExportFlags = c_uint32
SecExternalFormat = c_uint32
SecPadding = c_uint32
SSLProtocol = c_uint32
SSLCipherSuite = c_uint32
SecPolicyRef = POINTER(c_void_p)
CSSM_CC_HANDLE = c_uint64
CSSM_ALGORITHMS = c_uint32
CSSM_KEYUSE = c_uint32
SecItemImportExportKeyParameters = c_void_p
SecAccessRef = POINTER(c_void_p)
SecKeychainRef = c_void_p
SSLContextRef = POINTER(c_void_p)
SecTrustRef = POINTER(c_void_p)
SSLConnectionRef = c_uint32
SecTrustResultType = c_uint32
SecTrustOptionFlags = c_uint32
SecPolicySearchRef = c_void_p
CSSM_CERT_TYPE = c_uint32


class CSSM_DATA(Structure):  # noqa
    _fields_ = [
        ('Length', c_uint32),
        ('Data', c_char_p)
    ]


CSSM_OID = CSSM_DATA


class CSSM_APPLE_TP_OCSP_OPTIONS(Structure):  # noqa
    _fields_ = [
        ('Version', c_uint32),
        ('Flags', c_uint32),
        ('LocalResponder', POINTER(CSSM_DATA)),
        ('LocalResponderCert', POINTER(CSSM_DATA)),
    ]


class CSSM_APPLE_TP_CRL_OPTIONS(Structure):  # noqa
    _fields_ = [
        ('Version', c_uint32),
        ('CrlFlags', c_uint32),
        ('crlStore', c_void_p),
    ]


try:
    Security.SecRandomCopyBytes.argtypes = [
        SecRandomRef,
        c_size_t,
        c_char_p
    ]
    Security.SecRandomCopyBytes.restype = c_int

    Security.SecKeyCreateFromData.argtypes = [
        CFDictionaryRef,
        CFDataRef,
        POINTER(CFErrorRef)
    ]
    Security.SecKeyCreateFromData.restype = SecKeyRef

    Security.SecEncryptTransformCreate.argtypes = [
        SecKeyRef,
        POINTER(CFErrorRef)
    ]
    Security.SecEncryptTransformCreate.restype = SecTransformRef

    Security.SecDecryptTransformCreate.argtypes = [
        SecKeyRef,
        POINTER(CFErrorRef)
    ]
    Security.SecDecryptTransformCreate.restype = SecTransformRef

    Security.SecTransformSetAttribute.argtypes = [
        SecTransformRef,
        CFStringRef,
        CFTypeRef,
        POINTER(CFErrorRef)
    ]
    Security.SecTransformSetAttribute.restype = Boolean

    Security.SecTransformExecute.argtypes = [
        SecTransformRef,
        POINTER(CFErrorRef)
    ]
    Security.SecTransformExecute.restype = CFTypeRef

    Security.SecVerifyTransformCreate.argtypes = [
        SecKeyRef,
        CFDataRef,
        POINTER(CFErrorRef)
    ]
    Security.SecVerifyTransformCreate.restype = SecTransformRef

    Security.SecSignTransformCreate.argtypes = [
        SecKeyRef,
        POINTER(CFErrorRef)
    ]
    Security.SecSignTransformCreate.restype = SecTransformRef

    Security.SecCertificateCreateWithData.argtypes = [
        CFAllocatorRef,
        CFDataRef
    ]
    Security.SecCertificateCreateWithData.restype = SecCertificateRef

    Security.SecCertificateCopyPublicKey.argtypes = [
        SecCertificateRef,
        POINTER(SecKeyRef)
    ]
    Security.SecCertificateCopyPublicKey.restype = OSStatus

    Security.SecCopyErrorMessageString.argtypes = [
        OSStatus,
        c_void_p
    ]
    Security.SecCopyErrorMessageString.restype = CFStringRef

    Security.SecTrustCopyAnchorCertificates.argtypes = [
        POINTER(CFArrayRef)
    ]
    Security.SecTrustCopyAnchorCertificates.restype = OSStatus

    Security.SecCertificateCopyData.argtypes = [
        SecCertificateRef
    ]
    Security.SecCertificateCopyData.restype = CFDataRef

    Security.SecTrustSettingsCopyCertificates.argtypes = [
        SecTrustSettingsDomain,
        POINTER(CFArrayRef)
    ]
    Security.SecTrustSettingsCopyCertificates.restype = OSStatus

    Security.SecTrustSettingsCopyTrustSettings.argtypes = [
        SecCertificateRef,
        SecTrustSettingsDomain,
        POINTER(CFArrayRef)
    ]
    Security.SecTrustSettingsCopyTrustSettings.restype = OSStatus

    Security.SecPolicyCopyProperties.argtypes = [
        SecPolicyRef
    ]
    Security.SecPolicyCopyProperties.restype = CFDictionaryRef

    Security.SecPolicyGetTypeID.argtypes = []
    Security.SecPolicyGetTypeID.restype = CFTypeID

    Security.SecKeyEncrypt.argtypes = [
        SecKeyRef,
        SecPadding,
        c_char_p,
        c_size_t,
        c_char_p,
        POINTER(c_size_t)
    ]
    Security.SecKeyEncrypt.restype = OSStatus

    Security.SecKeyDecrypt.argtypes = [
        SecKeyRef,
        SecPadding,
        c_char_p,
        c_size_t,
        c_char_p,
        POINTER(c_size_t)
    ]
    Security.SecKeyDecrypt.restype = OSStatus

    Security.SecKeyRawSign.argtypes = [
        SecKeyRef,
        SecPadding,
        c_char_p,
        c_size_t,
        c_char_p,
        POINTER(c_size_t)
    ]
    Security.SecKeyRawSign.restype = OSStatus

    Security.SecKeyRawVerify.argtypes = [
        SecKeyRef,
        SecPadding,
        c_char_p,
        c_size_t,
        c_char_p,
        c_size_t
    ]
    Security.SecKeyRawVerify.restype = OSStatus

    Security.SecKeyGeneratePair.argtypes = [
        CFDictionaryRef,
        POINTER(SecKeyRef),
        POINTER(SecKeyRef)
    ]
    Security.SecKeyGeneratePair.restype = OSStatus

    Security.SecAccessCreate.argtypes = [
        CFStringRef,
        CFArrayRef,
        POINTER(SecAccessRef)
    ]
    Security.SecAccessCreate.restype = OSStatus

    Security.SecKeyCreatePair.argtypes = [
        SecKeychainRef,
        CSSM_ALGORITHMS,
        c_uint32,
        CSSM_CC_HANDLE,
        CSSM_KEYUSE,
        c_uint32,
        CSSM_KEYUSE,
        c_uint32,
        SecAccessRef,
        POINTER(SecKeyRef),
        POINTER(SecKeyRef)
    ]
    Security.SecKeyCreatePair.restype = OSStatus

    Security.SecItemExport.argtypes = [
        CFTypeRef,
        SecExternalFormat,
        SecItemImportExportFlags,
        SecItemImportExportKeyParameters,
        POINTER(CFDataRef)
    ]
    Security.SecItemExport.restype = OSStatus

    Security.SecKeychainItemDelete.argtypes = [
        SecKeyRef
    ]
    Security.SecKeychainItemDelete.restype = OSStatus

    SSLReadFunc = CFUNCTYPE(OSStatus, SSLConnectionRef, POINTER(c_byte), POINTER(c_size_t))
    SSLWriteFunc = CFUNCTYPE(OSStatus, SSLConnectionRef, POINTER(c_byte), POINTER(c_size_t))

    Security.SSLSetIOFuncs.argtypes = [
        SSLContextRef,
        SSLReadFunc,
        SSLWriteFunc
    ]
    Security.SSLSetIOFuncs.restype = OSStatus

    Security.SSLSetPeerID.argtypes = [
        SSLContextRef,
        c_char_p,
        c_size_t
    ]
    Security.SSLSetPeerID.restype = OSStatus

    Security.SSLSetCertificateAuthorities.argtypes = [
        SSLContextRef,
        CFTypeRef,
        Boolean
    ]
    Security.SSLSetCertificateAuthorities.restype = OSStatus

    Security.SecTrustSetPolicies.argtypes = [
        SecTrustRef,
        CFArrayRef
    ]
    Security.SecTrustSetPolicies.restype = OSStatus

    Security.SecPolicyCreateSSL.argtypes = [
        Boolean,
        CFStringRef
    ]
    Security.SecPolicyCreateSSL.restype = SecPolicyRef

    Security.SecPolicySearchCreate.argtypes = [
        CSSM_CERT_TYPE,
        POINTER(CSSM_OID),
        POINTER(CSSM_DATA),
        POINTER(SecPolicySearchRef)
    ]
    Security.SecPolicySearchCreate.restype = OSStatus

    Security.SecPolicySearchCopyNext.argtypes = [
        SecPolicySearchRef,
        POINTER(SecPolicyRef)
    ]
    Security.SecPolicySearchCopyNext.restype = OSStatus

    Security.SecPolicySetValue.argtypes = [
        SecPolicyRef,
        POINTER(CSSM_DATA)
    ]
    Security.SecPolicySetValue.restype = OSStatus

    Security.SSLSetConnection.argtypes = [
        SSLContextRef,
        SSLConnectionRef
    ]
    Security.SSLSetConnection.restype = OSStatus

    Security.SSLSetPeerDomainName.argtypes = [
        SSLContextRef,
        c_char_p,
        c_size_t
    ]
    Security.SSLSetPeerDomainName.restype = OSStatus

    Security.SSLHandshake.argtypes = [
        SSLContextRef
    ]
    Security.SSLHandshake.restype = OSStatus

    Security.SSLGetBufferedReadSize.argtypes = [
        SSLContextRef,
        POINTER(c_size_t)
    ]
    Security.SSLGetBufferedReadSize.restype = OSStatus

    Security.SSLRead.argtypes = [
        SSLContextRef,
        c_char_p,
        c_size_t,
        POINTER(c_size_t)
    ]
    Security.SSLRead.restype = OSStatus

    Security.SSLWrite.argtypes = [
        SSLContextRef,
        c_char_p,
        c_size_t,
        POINTER(c_size_t)
    ]
    Security.SSLWrite.restype = OSStatus

    Security.SSLClose.argtypes = [
        SSLContextRef
    ]
    Security.SSLClose.restype = OSStatus

    Security.SSLGetNumberSupportedCiphers.argtypes = [
        SSLContextRef,
        POINTER(c_size_t)
    ]
    Security.SSLGetNumberSupportedCiphers.restype = OSStatus

    Security.SSLGetSupportedCiphers.argtypes = [
        SSLContextRef,
        POINTER(SSLCipherSuite),
        POINTER(c_size_t)
    ]
    Security.SSLGetSupportedCiphers.restype = OSStatus

    Security.SSLSetEnabledCiphers.argtypes = [
        SSLContextRef,
        POINTER(SSLCipherSuite),
        c_size_t
    ]
    Security.SSLSetEnabledCiphers.restype = OSStatus

    Security.SSLGetNumberEnabledCiphers.argtype = [
        SSLContextRef,
        POINTER(c_size_t)
    ]
    Security.SSLGetNumberEnabledCiphers.restype = OSStatus

    Security.SSLGetEnabledCiphers.argtypes = [
        SSLContextRef,
        POINTER(SSLCipherSuite),
        POINTER(c_size_t)
    ]
    Security.SSLGetEnabledCiphers.restype = OSStatus

    Security.SSLGetNegotiatedCipher.argtypes = [
        SSLContextRef,
        POINTER(SSLCipherSuite)
    ]
    Security.SSLGetNegotiatedCipher.restype = OSStatus

    Security.SSLGetNegotiatedProtocolVersion.argtypes = [
        SSLContextRef,
        POINTER(SSLProtocol)
    ]
    Security.SSLGetNegotiatedProtocolVersion.restype = OSStatus

    Security.SSLCopyPeerTrust.argtypes = [
        SSLContextRef,
        POINTER(SecTrustRef)
    ]
    Security.SSLCopyPeerTrust.restype = OSStatus

    Security.SecTrustGetCssmResultCode.argtypes = [
        SecTrustRef,
        POINTER(OSStatus)
    ]
    Security.SecTrustGetCssmResultCode.restype = OSStatus

    Security.SecTrustGetCertificateCount.argtypes = [
        SecTrustRef
    ]
    Security.SecTrustGetCertificateCount.restype = CFIndex

    Security.SecTrustGetCertificateAtIndex.argtypes = [
        SecTrustRef,
        CFIndex
    ]
    Security.SecTrustGetCertificateAtIndex.restype = SecCertificateRef

    Security.SecTrustSetAnchorCertificates.argtypes = [
        SecTrustRef,
        CFArrayRef
    ]
    Security.SecTrustSetAnchorCertificates.restype = OSStatus

    Security.SecTrustSetAnchorCertificatesOnly.argstypes = [
        SecTrustRef,
        Boolean
    ]
    Security.SecTrustSetAnchorCertificatesOnly.restype = OSStatus

    Security.SecTrustEvaluate.argtypes = [
        SecTrustRef,
        POINTER(SecTrustResultType)
    ]
    Security.SecTrustEvaluate.restype = OSStatus

    if version_info < (10, 8):
        Security.SSLNewContext.argtypes = [
            Boolean,
            POINTER(SSLContextRef)
        ]
        Security.SSLNewContext.restype = OSStatus

        Security.SSLDisposeContext.argtypes = [
            SSLContextRef
        ]
        Security.SSLDisposeContext.restype = OSStatus

        Security.SSLSetEnableCertVerify.argtypes = [
            SSLContextRef,
            Boolean
        ]
        Security.SSLSetEnableCertVerify.restype = OSStatus

        Security.SSLSetProtocolVersionEnabled.argtypes = [
            SSLContextRef,
            SSLProtocol,
            Boolean
        ]
        Security.SSLSetProtocolVersionEnabled.restype = OSStatus

    else:
        SSLProtocolSide = c_uint32
        SSLConnectionType = c_uint32
        SSLSessionOption = c_uint32

        Security.SSLCreateContext.argtypes = [
            CFAllocatorRef,
            SSLProtocolSide,
            SSLConnectionType
        ]
        Security.SSLCreateContext.restype = SSLContextRef

        Security.SSLSetSessionOption.argtypes = [
            SSLContextRef,
            SSLSessionOption,
            Boolean
        ]
        Security.SSLSetSessionOption.restype = OSStatus

        Security.SSLSetProtocolVersionMin.argtypes = [
            SSLContextRef,
            SSLProtocol
        ]
        Security.SSLSetProtocolVersionMin.restype = OSStatus

        Security.SSLSetProtocolVersionMax.argtypes = [
            SSLContextRef,
            SSLProtocol
        ]
        Security.SSLSetProtocolVersionMax.restype = OSStatus

    setattr(Security, 'SSLReadFunc', SSLReadFunc)
    setattr(Security, 'SSLWriteFunc', SSLWriteFunc)
    setattr(Security, 'SSLContextRef', SSLContextRef)
    setattr(Security, 'SSLProtocol', SSLProtocol)
    setattr(Security, 'SSLCipherSuite', SSLCipherSuite)
    setattr(Security, 'SecTrustRef', SecTrustRef)
    setattr(Security, 'SecTrustResultType', SecTrustResultType)
    setattr(Security, 'OSStatus', OSStatus)

    setattr(Security, 'SecAccessRef', SecAccessRef)
    setattr(Security, 'SecKeyRef', SecKeyRef)

    setattr(Security, 'SecPolicySearchRef', SecPolicySearchRef)
    setattr(Security, 'SecPolicyRef', SecPolicyRef)

    setattr(Security, 'CSSM_DATA', CSSM_DATA)
    setattr(Security, 'CSSM_OID', CSSM_OID)
    setattr(Security, 'CSSM_APPLE_TP_OCSP_OPTIONS', CSSM_APPLE_TP_OCSP_OPTIONS)
    setattr(Security, 'CSSM_APPLE_TP_CRL_OPTIONS', CSSM_APPLE_TP_CRL_OPTIONS)

    setattr(Security, 'kSecRandomDefault', SecRandomRef.in_dll(Security, 'kSecRandomDefault'))

    setattr(Security, 'kSecPaddingKey', CFStringRef.in_dll(Security, 'kSecPaddingKey'))
    setattr(Security, 'kSecPaddingPKCS7Key', CFStringRef.in_dll(Security, 'kSecPaddingPKCS7Key'))
    setattr(Security, 'kSecPaddingPKCS5Key', CFStringRef.in_dll(Security, 'kSecPaddingPKCS5Key'))
    setattr(Security, 'kSecPaddingPKCS1Key', CFStringRef.in_dll(Security, 'kSecPaddingPKCS1Key'))
    setattr(Security, 'kSecPaddingOAEPKey', CFStringRef.in_dll(Security, 'kSecPaddingOAEPKey'))
    setattr(Security, 'kSecPaddingNoneKey', CFStringRef.in_dll(Security, 'kSecPaddingNoneKey'))
    setattr(Security, 'kSecModeCBCKey', CFStringRef.in_dll(Security, 'kSecModeCBCKey'))
    setattr(
        Security,
        'kSecTransformInputAttributeName',
        CFStringRef.in_dll(Security, 'kSecTransformInputAttributeName')
    )
    setattr(Security, 'kSecDigestTypeAttribute', CFStringRef.in_dll(Security, 'kSecDigestTypeAttribute'))
    setattr(Security, 'kSecDigestLengthAttribute', CFStringRef.in_dll(Security, 'kSecDigestLengthAttribute'))
    setattr(Security, 'kSecIVKey', CFStringRef.in_dll(Security, 'kSecIVKey'))

    setattr(Security, 'kSecAttrKeyClass', CFStringRef.in_dll(Security, 'kSecAttrKeyClass'))
    setattr(Security, 'kSecAttrKeyClassPublic', CFTypeRef.in_dll(Security, 'kSecAttrKeyClassPublic'))
    setattr(Security, 'kSecAttrKeyClassPrivate', CFTypeRef.in_dll(Security, 'kSecAttrKeyClassPrivate'))

    setattr(Security, 'kSecDigestSHA1', CFStringRef.in_dll(Security, 'kSecDigestSHA1'))
    setattr(Security, 'kSecDigestSHA2', CFStringRef.in_dll(Security, 'kSecDigestSHA2'))
    setattr(Security, 'kSecDigestMD5', CFStringRef.in_dll(Security, 'kSecDigestMD5'))

    setattr(Security, 'kSecAttrKeyType', CFStringRef.in_dll(Security, 'kSecAttrKeyType'))

    setattr(Security, 'kSecAttrKeyTypeRSA', CFTypeRef.in_dll(Security, 'kSecAttrKeyTypeRSA'))
    setattr(Security, 'kSecAttrKeyTypeDSA', CFTypeRef.in_dll(Security, 'kSecAttrKeyTypeDSA'))
    setattr(Security, 'kSecAttrKeyTypeECDSA', CFTypeRef.in_dll(Security, 'kSecAttrKeyTypeECDSA'))

    setattr(Security, 'kSecAttrKeySizeInBits', CFStringRef.in_dll(Security, 'kSecAttrKeySizeInBits'))
    setattr(Security, 'kSecAttrLabel', CFStringRef.in_dll(Security, 'kSecAttrLabel'))

    setattr(Security, 'kSecAttrCanSign', CFTypeRef.in_dll(Security, 'kSecAttrCanSign'))
    setattr(Security, 'kSecAttrCanVerify', CFTypeRef.in_dll(Security, 'kSecAttrCanVerify'))

    setattr(Security, 'kSecAttrKeyTypeAES', CFTypeRef.in_dll(Security, 'kSecAttrKeyTypeAES'))
    setattr(Security, 'kSecAttrKeyTypeRC4', CFTypeRef.in_dll(Security, 'kSecAttrKeyTypeRC4'))
    setattr(Security, 'kSecAttrKeyTypeRC2', CFTypeRef.in_dll(Security, 'kSecAttrKeyTypeRC2'))
    setattr(Security, 'kSecAttrKeyType3DES', CFTypeRef.in_dll(Security, 'kSecAttrKeyType3DES'))
    setattr(Security, 'kSecAttrKeyTypeDES', CFTypeRef.in_dll(Security, 'kSecAttrKeyTypeDES'))

except (AttributeError):
    raise FFIEngineError('Error initializing ctypes')
