# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import os

from .._asn1 import Certificate, TrustedCertificate, unarmor
from .._errors import pretty_message


__all__ = [
    'extract_from_system',
    'system_path',
]


def system_path():
    """
    Tries to find a CA certs bundle in common locations

    :raises:
        OSError - when no valid CA certs bundle was found on the filesystem

    :return:
        The full filesystem path to a CA certs bundle file
    """

    ca_path = None

    # Common CA cert paths
    paths = [
        '/usr/lib/ssl/certs/ca-certificates.crt',
        '/etc/ssl/certs/ca-certificates.crt',
        '/etc/ssl/certs/ca-bundle.crt',
        '/etc/pki/tls/certs/ca-bundle.crt',
        '/etc/ssl/ca-bundle.pem',
        '/usr/local/share/certs/ca-root-nss.crt',
        '/etc/ssl/cert.pem'
    ]

    # First try SSL_CERT_FILE
    if 'SSL_CERT_FILE' in os.environ:
        paths.insert(0, os.environ['SSL_CERT_FILE'])

    for path in paths:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            ca_path = path
            break

    if not ca_path:
        raise OSError(pretty_message(
            '''
            Unable to find a CA certs bundle in common locations - try
            setting the SSL_CERT_FILE environmental variable
            '''
        ))

    return ca_path


def extract_from_system(cert_callback=None, callback_only_on_failure=False):
    """
    Extracts trusted CA certs from the system CA cert bundle

    :param cert_callback:
        A callback that is called once for each certificate in the trust store.
        It should accept two parameters: an asn1crypto.x509.Certificate object,
        and a reason. The reason will be None if the certificate is being
        exported, otherwise it will be a unicode string of the reason it won't.

    :param callback_only_on_failure:
        A boolean - if the callback should only be called when a certificate is
        not exported.

    :return:
        A list of 3-element tuples:
         - 0: a byte string of a DER-encoded certificate
         - 1: a set of unicode strings that are OIDs of purposes to trust the
              certificate for
         - 2: a set of unicode strings that are OIDs of purposes to reject the
              certificate for
    """

    all_purposes = '2.5.29.37.0'
    ca_path = system_path()

    output = []
    with open(ca_path, 'rb') as f:
        for armor_type, _, cert_bytes in unarmor(f.read(), multiple=True):
            # Without more info, a certificate is trusted for all purposes
            if armor_type == 'CERTIFICATE':
                if cert_callback:
                    cert_callback(Certificate.load(cert_bytes), None)
                output.append((cert_bytes, set(), set()))

            # The OpenSSL TRUSTED CERTIFICATE construct adds OIDs for trusted
            # and rejected purposes, so we extract that info.
            elif armor_type == 'TRUSTED CERTIFICATE':
                cert, aux = TrustedCertificate.load(cert_bytes)
                reject_all = False
                trust_oids = set()
                reject_oids = set()
                for purpose in aux['trust']:
                    if purpose.dotted == all_purposes:
                        trust_oids = set([purpose.dotted])
                        break
                    trust_oids.add(purpose.dotted)
                for purpose in aux['reject']:
                    if purpose.dotted == all_purposes:
                        reject_all = True
                        break
                    reject_oids.add(purpose.dotted)
                if reject_all:
                    if cert_callback:
                        cert_callback(cert, 'explicitly distrusted')
                    continue
                if cert_callback and not callback_only_on_failure:
                    cert_callback(cert, None)
                output.append((cert.dump(), trust_oids, reject_oids))

    return output
