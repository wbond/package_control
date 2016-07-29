# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import hashlib
import sys

from .._ffi import new, unwrap
from ._core_foundation import CoreFoundation, CFHelpers
from ._security import Security, SecurityConst, handle_sec_error

if sys.version_info < (3,):
    range = xrange  # noqa


__all__ = [
    'extract_from_system',
    'system_path',
]


def system_path():
    return None


def extract_from_system():
    """
    Extracts trusted CA certificates from the OS X trusted root keychain.

    :raises:
        OSError - when an error is returned by the OS crypto library

    :return:
        A list of 3-element tuples:
         - 0: a byte string of a DER-encoded certificate
         - 1: a set of unicode strings that are OIDs of purposes to trust the
              certificate for
         - 2: a set of unicode strings that are OIDs of purposes to reject the
              certificate for
    """

    certs_pointer_pointer = new(CoreFoundation, 'CFArrayRef *')
    res = Security.SecTrustCopyAnchorCertificates(certs_pointer_pointer)
    handle_sec_error(res)

    certs_pointer = unwrap(certs_pointer_pointer)

    certificates = {}
    trust_info = {}

    all_purposes = '2.5.29.37.0'
    default_trust = (set(), set())

    length = CoreFoundation.CFArrayGetCount(certs_pointer)
    for index in range(0, length):
        cert_pointer = CoreFoundation.CFArrayGetValueAtIndex(certs_pointer, index)

        data_pointer = Security.SecCertificateCopyData(cert_pointer)
        der_cert = CFHelpers.cf_data_to_bytes(data_pointer)
        CoreFoundation.CFRelease(data_pointer)

        cert_hash = hashlib.sha1(der_cert).digest()
        certificates[cert_hash] = der_cert

    CoreFoundation.CFRelease(certs_pointer)

    for domain in [SecurityConst.kSecTrustSettingsDomainUser, SecurityConst.kSecTrustSettingsDomainAdmin]:
        cert_trust_settings_pointer_pointer = new(CoreFoundation, 'CFArrayRef *')
        res = Security.SecTrustSettingsCopyCertificates(domain, cert_trust_settings_pointer_pointer)
        if res == SecurityConst.errSecNoTrustSettings:
            continue
        handle_sec_error(res)

        cert_trust_settings_pointer = unwrap(cert_trust_settings_pointer_pointer)

        length = CoreFoundation.CFArrayGetCount(cert_trust_settings_pointer)
        for index in range(0, length):
            cert_pointer = CoreFoundation.CFArrayGetValueAtIndex(cert_trust_settings_pointer, index)

            trust_settings_pointer_pointer = new(CoreFoundation, 'CFArrayRef *')
            res = Security.SecTrustSettingsCopyTrustSettings(cert_pointer, domain, trust_settings_pointer_pointer)
            # In OS X 10.11, this value started being seen. From the comments in
            # the Security Framework Reference, the lack of any settings should
            # indicate "always strut this certificate"
            if res == SecurityConst.errSecItemNotFound:
                continue
            handle_sec_error(res)

            trust_settings_pointer = unwrap(trust_settings_pointer_pointer)

            trust_oids = set()
            reject_oids = set()
            settings_length = CoreFoundation.CFArrayGetCount(trust_settings_pointer)
            for settings_index in range(0, settings_length):
                settings_dict_entry = CoreFoundation.CFArrayGetValueAtIndex(trust_settings_pointer, settings_index)
                settings_dict = CFHelpers.cf_dictionary_to_dict(settings_dict_entry)

                # No policy OID means the trust result is for all purposes
                policy_oid = settings_dict.get('kSecTrustSettingsPolicy', {}).get('SecPolicyOid', all_purposes)

                # 0 = kSecTrustSettingsResultInvalid
                # 1 = kSecTrustSettingsResultTrustRoot
                # 2 = kSecTrustSettingsResultTrustAsRoot
                # 3 = kSecTrustSettingsResultDeny
                # 4 = kSecTrustSettingsResultUnspecified
                trust_result = settings_dict.get('kSecTrustSettingsResult', 1)
                should_trust = trust_result != 0 and trust_result != 3

                if should_trust:
                    trust_oids.add(policy_oid)
                else:
                    reject_oids.add(policy_oid)

            data_pointer = Security.SecCertificateCopyData(cert_pointer)
            der_cert = CFHelpers.cf_data_to_bytes(data_pointer)
            CoreFoundation.CFRelease(data_pointer)

            cert_hash = hashlib.sha1(der_cert).digest()

            # If rejected for all purposes, we don't export the certificate
            if all_purposes in reject_oids:
                del certificates[cert_hash]
            else:
                if all_purposes in trust_oids:
                    trust_oids = set([all_purposes])
                trust_info[cert_hash] = (trust_oids, reject_oids)

            CoreFoundation.CFRelease(trust_settings_pointer)

        CoreFoundation.CFRelease(cert_trust_settings_pointer)

    output = []
    for cert_hash in certificates:
        cert_trust_info = trust_info.get(cert_hash, default_trust)
        output.append((certificates[cert_hash], cert_trust_info[0], cert_trust_info[1]))
    return output
