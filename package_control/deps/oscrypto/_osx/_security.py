# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from .._ffi import FFIEngineError, null

try:
    from ._security_cffi import Security, version_info as osx_version_info
    from ._core_foundation_cffi import CoreFoundation, CFHelpers
except (FFIEngineError, ImportError):
    from ._security_ctypes import Security, version_info as osx_version_info
    from ._core_foundation_ctypes import CoreFoundation, CFHelpers


__all__ = [
    'handle_sec_error',
    'osx_version_info',
    'Security',
    'SecurityConst',
]


def handle_sec_error(error, exception_class=None):
    """
    Checks a Security OSStatus error code and throws an exception if there is an
    error to report

    :param error:
        An OSStatus

    :param exception_class:
        The exception class to use for the exception if an error occurred

    :raises:
        OSError - when the OSStatus contains an error
    """

    if error == 0:
        return

    cf_error_string = Security.SecCopyErrorMessageString(error, null())
    output = CFHelpers.cf_string_to_unicode(cf_error_string)
    CoreFoundation.CFRelease(cf_error_string)

    if output is None or output == '':
        output = 'OSStatus %s' % error

    if exception_class is None:
        exception_class = OSError

    raise exception_class(output)


def _extract_policy_properties(value):
    properties_dict = Security.SecPolicyCopyProperties(value)
    return CFHelpers.cf_dictionary_to_dict(properties_dict)


CFHelpers.register_native_mapping(
    Security.SecPolicyGetTypeID(),
    _extract_policy_properties
)


class SecurityConst():
    kSecTrustSettingsDomainUser = 0
    kSecTrustSettingsDomainAdmin = 1
    kSecTrustSettingsDomainSystem = 2

    kSecTrustResultProceed = 1
    kSecTrustResultUnspecified = 4
    kSecTrustOptionImplicitAnchors = 0x00000040

    kSSLSessionOptionBreakOnServerAuth = 0

    kSSLProtocol2 = 1
    kSSLProtocol3 = 2
    kTLSProtocol1 = 4
    kTLSProtocol11 = 7
    kTLSProtocol12 = 8

    kSSLClientSide = 1
    kSSLStreamType = 0

    errSSLProtocol = -9800
    errSSLWouldBlock = -9803
    errSSLClosedGraceful = -9805
    errSSLClosedNoNotify = -9816
    errSSLClosedAbort = -9806

    errSSLXCertChainInvalid = -9807
    errSSLCrypto = -9809
    errSSLInternal = -9810
    errSSLCertExpired = -9814
    errSSLCertNotYetValid = -9815
    errSSLUnknownRootCert = -9812
    errSSLNoRootCert = -9813
    errSSLHostNameMismatch = -9843
    errSSLPeerHandshakeFail = -9824
    errSSLPeerUserCancelled = -9839
    errSSLWeakPeerEphemeralDHKey = -9850
    errSSLServerAuthCompleted = -9841
    errSSLRecordOverflow = -9847

    CSSMERR_APPLETP_HOSTNAME_MISMATCH = -2147408896
    CSSMERR_TP_CERT_EXPIRED = -2147409654
    CSSMERR_TP_CERT_NOT_VALID_YET = -2147409653
    CSSMERR_TP_CERT_REVOKED = -2147409652
    CSSMERR_TP_NOT_TRUSTED = -2147409622

    CSSM_CERT_X_509v3 = 0x00000004

    APPLE_TP_REVOCATION_CRL = b'*\x86H\x86\xf7cd\x01\x06'
    APPLE_TP_REVOCATION_OCSP = b'*\x86H\x86\xf7cd\x01\x07'

    CSSM_APPLE_TP_OCSP_OPTS_VERSION = 0
    CSSM_TP_ACTION_OCSP_DISABLE_NET = 0x00000004
    CSSM_TP_ACTION_OCSP_CACHE_READ_DISABLE = 0x00000008

    CSSM_APPLE_TP_CRL_OPTS_VERSION = 0

    errSecVerifyFailed = -67808
    errSecNoTrustSettings = -25263
    errSecItemNotFound = -25300
    errSecInvalidTrustSettings = -25262

    kSecPaddingNone = 0
    kSecPaddingPKCS1 = 1

    CSSM_KEYUSE_SIGN = 0x00000004
    CSSM_KEYUSE_VERIFY = 0x00000008

    CSSM_ALGID_DH = 2
    CSSM_ALGID_DSA = 43
    CSSM_KEYATTR_PERMANENT = 0x00000001
    CSSM_KEYATTR_EXTRACTABLE = 0x00000020
