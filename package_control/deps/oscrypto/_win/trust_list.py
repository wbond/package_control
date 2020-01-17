# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import datetime
import hashlib
import struct

from .._asn1 import Certificate
from .._ffi import (
    array_from_pointer,
    buffer_from_bytes,
    bytes_from_buffer,
    cast,
    deref,
    is_null,
    new,
    null,
    struct_from_buffer,
    unwrap,
)
from ._crypt32 import crypt32, Crypt32Const, get_error, handle_error
from .._types import str_cls


__all__ = [
    'extract_from_system',
    'system_path',
]


def system_path():
    return None


def extract_from_system(cert_callback=None, callback_only_on_failure=False):
    """
    Extracts trusted CA certificates from the Windows certificate store

    :param cert_callback:
        A callback that is called once for each certificate in the trust store.
        It should accept two parameters: an asn1crypto.x509.Certificate object,
        and a reason. The reason will be None if the certificate is being
        exported, otherwise it will be a unicode string of the reason it won't.

    :param callback_only_on_failure:
        A boolean - if the callback should only be called when a certificate is
        not exported.

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

    certificates = {}
    processed = {}

    now = datetime.datetime.utcnow()

    for store in ["ROOT", "CA"]:
        store_handle = crypt32.CertOpenSystemStoreW(null(), store)
        handle_error(store_handle)

        context_pointer = null()
        while True:
            context_pointer = crypt32.CertEnumCertificatesInStore(store_handle, context_pointer)
            if is_null(context_pointer):
                break
            context = unwrap(context_pointer)

            trust_all = False
            data = None
            digest = None

            if context.dwCertEncodingType != Crypt32Const.X509_ASN_ENCODING:
                continue

            data = bytes_from_buffer(context.pbCertEncoded, int(context.cbCertEncoded))
            digest = hashlib.sha1(data).digest()
            if digest in processed:
                continue

            processed[digest] = True
            cert_info = unwrap(context.pCertInfo)

            not_before_seconds = _convert_filetime_to_timestamp(cert_info.NotBefore)
            try:
                not_before = datetime.datetime.fromtimestamp(not_before_seconds)
                if not_before > now:
                    if cert_callback:
                        cert_callback(Certificate.load(data), 'not yet valid')
                    continue
            except (ValueError, OSError):
                # If there is an error converting the not before timestamp,
                # it is almost certainly because it is from too long ago,
                # which means the cert is definitely valid by now.
                pass

            not_after_seconds = _convert_filetime_to_timestamp(cert_info.NotAfter)
            try:
                not_after = datetime.datetime.fromtimestamp(not_after_seconds)
                if not_after < now:
                    if cert_callback:
                        cert_callback(Certificate.load(data), 'no longer valid')
                    continue
            except (ValueError, OSError) as e:
                # The only reason we would get an exception here is if the
                # expiration time is so far in the future that it can't be
                # used as a timestamp, or it is before 0. If it is very far
                # in the future, the cert is still valid, so we only raise
                # an exception if the timestamp is less than zero.
                if not_after_seconds < 0:
                    message = e.args[0] + ' - ' + str_cls(not_after_seconds)
                    e.args = (message,) + e.args[1:]
                    raise e

            trust_oids = set()
            reject_oids = set()

            # Here we grab the extended key usage properties that Windows
            # layers on top of the extended key usage extension that is
            # part of the certificate itself. For highest security, users
            # should only use certificates for the intersection of the two
            # lists of purposes. However, many seen to treat the OS trust
            # list as an override.
            to_read = new(crypt32, 'DWORD *', 0)
            res = crypt32.CertGetEnhancedKeyUsage(
                context_pointer,
                Crypt32Const.CERT_FIND_PROP_ONLY_ENHKEY_USAGE_FLAG,
                null(),
                to_read
            )

            # Per the Microsoft documentation, if CRYPT_E_NOT_FOUND is returned
            # from get_error(), it means the certificate is valid for all purposes
            error_code, _ = get_error()
            if not res and error_code != Crypt32Const.CRYPT_E_NOT_FOUND:
                handle_error(res)

            if error_code == Crypt32Const.CRYPT_E_NOT_FOUND:
                trust_all = True
            else:
                usage_buffer = buffer_from_bytes(deref(to_read))
                res = crypt32.CertGetEnhancedKeyUsage(
                    context_pointer,
                    Crypt32Const.CERT_FIND_PROP_ONLY_ENHKEY_USAGE_FLAG,
                    cast(crypt32, 'CERT_ENHKEY_USAGE *', usage_buffer),
                    to_read
                )
                handle_error(res)

                key_usage_pointer = struct_from_buffer(crypt32, 'CERT_ENHKEY_USAGE', usage_buffer)
                key_usage = unwrap(key_usage_pointer)

                # Having no enhanced usage properties means a cert is distrusted
                if key_usage.cUsageIdentifier == 0:
                    if cert_callback:
                        cert_callback(Certificate.load(data), 'explicitly distrusted')
                    continue

                oids = array_from_pointer(
                    crypt32,
                    'LPCSTR',
                    key_usage.rgpszUsageIdentifier,
                    key_usage.cUsageIdentifier
                )
                for oid in oids:
                    trust_oids.add(oid.decode('ascii'))

            cert = None

            # If the certificate is not under blanket trust, we have to
            # determine what purposes it is rejected for by diffing the
            # set of OIDs from the certificate with the OIDs that are
            # trusted.
            if not trust_all:
                cert = Certificate.load(data)
                if cert.extended_key_usage_value:
                    for cert_oid in cert.extended_key_usage_value:
                        oid = cert_oid.dotted
                        if oid not in trust_oids:
                            reject_oids.add(oid)

            if cert_callback and not callback_only_on_failure:
                if cert is None:
                    cert = Certificate.load(data)
                cert_callback(cert, None)

            certificates[digest] = (data, trust_oids, reject_oids)

        result = crypt32.CertCloseStore(store_handle, 0)
        handle_error(result)
        store_handle = None

    return certificates.values()


def _convert_filetime_to_timestamp(filetime):
    """
    Windows returns times as 64-bit unsigned longs that are the number
    of hundreds of nanoseconds since Jan 1 1601. This converts it to
    a datetime object.

    :param filetime:
        A FILETIME struct object

    :return:
        An integer unix timestamp
    """

    hundreds_nano_seconds = struct.unpack(
        b'>Q',
        struct.pack(
            b'>LL',
            filetime.dwHighDateTime,
            filetime.dwLowDateTime
        )
    )[0]
    seconds_since_1601 = hundreds_nano_seconds / 10000000
    return seconds_since_1601 - 11644473600  # Seconds from Jan 1 1601 to Jan 1 1970
