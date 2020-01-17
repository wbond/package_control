# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import os
import time
import sys
import tempfile
import threading

from ._asn1 import armor, Certificate
from ._errors import pretty_message
from .errors import CACertsError

if sys.platform == 'win32':
    from ._win.trust_list import extract_from_system, system_path
elif sys.platform == 'darwin':
    from ._mac.trust_list import extract_from_system, system_path
else:
    from ._linux_bsd.trust_list import extract_from_system, system_path


__all__ = [
    'clear_cache',
    'get_list',
    'get_path',
]


path_lock = threading.Lock()
memory_lock = threading.Lock()
_module_values = {
    'last_update': None,
    'certs': None
}

_oid_map = {
    # apple_smime -> email_protection
    '1.2.840.113635.100.1.8': set(['1.3.6.1.5.5.7.3.4']),
    # apple_code_signing -> code_signing
    '1.2.840.113635.100.1.16': set(['1.3.6.1.5.5.7.3.3']),
    # apple_time_stamping -> time_stamping
    '1.2.840.113635.100.1.20': set(['1.3.6.1.5.5.7.3.8']),
    # microsoft_time_stamp_signing -> time_stamping
    '1.3.6.1.4.1.311.10.3.2': set(['1.3.6.1.5.5.7.3.8']),
    # apple_ssl -> (server_auth, client_auth)
    '1.2.840.113635.100.1.3': set([
        '1.3.6.1.5.5.7.3.1',
        '1.3.6.1.5.5.7.3.2',
    ]),
    # apple_eap -> (eap_over_ppp, eap_over_lan)
    '1.2.840.113635.100.1.9': set([
        '1.3.6.1.5.5.7.3.13',
        '1.3.6.1.5.5.7.3.14',
    ]),
    # apple_ipsec -> (ipsec_end_system, ipsec_tunnel, ipsec_user, ipsec_ike)
    '1.2.840.113635.100.1.11': set([
        '1.3.6.1.5.5.7.3.5',
        '1.3.6.1.5.5.7.3.6',
        '1.3.6.1.5.5.7.3.7',
        '1.3.6.1.5.5.7.3.17',
    ])
}


def get_path(temp_dir=None, cache_length=24, cert_callback=None):
    """
    Get the filesystem path to a file that contains OpenSSL-compatible CA certs.

    On OS X and Windows, there are extracted from the system certificate store
    and cached in a file on the filesystem. This path should not be writable
    by other users, otherwise they could inject CA certs into the trust list.

    :param temp_dir:
        The temporary directory to cache the CA certs in on OS X and Windows.
        Needs to have secure permissions so other users can not modify the
        contents.

    :param cache_length:
        The number of hours to cache the CA certs on OS X and Windows

    :param cert_callback:
        A callback that is called once for each certificate in the trust store.
        It should accept two parameters: an asn1crypto.x509.Certificate object,
        and a reason. The reason will be None if the certificate is being
        exported, otherwise it will be a unicode string of the reason it won't.
        This is only called on Windows and OS X when passed to this function.

    :raises:
        oscrypto.errors.CACertsError - when an error occurs exporting/locating certs

    :return:
        The full filesystem path to a CA certs file
    """

    ca_path, temp = _ca_path(temp_dir)

    # Windows and OS X
    if temp and _cached_path_needs_update(ca_path, cache_length):
        empty_set = set()

        any_purpose = '2.5.29.37.0'
        apple_ssl = '1.2.840.113635.100.1.3'
        win_server_auth = '1.3.6.1.5.5.7.3.1'

        with path_lock:
            if _cached_path_needs_update(ca_path, cache_length):
                with open(ca_path, 'wb') as f:
                    for cert, trust_oids, reject_oids in extract_from_system(cert_callback, True):
                        if sys.platform == 'darwin':
                            if trust_oids != empty_set and any_purpose not in trust_oids \
                                    and apple_ssl not in trust_oids:
                                if cert_callback:
                                    cert_callback(Certificate.load(cert), 'implicitly distrusted for TLS')
                                continue
                            if reject_oids != empty_set and (apple_ssl in reject_oids
                                                             or any_purpose in reject_oids):
                                if cert_callback:
                                    cert_callback(Certificate.load(cert), 'explicitly distrusted for TLS')
                                continue
                        elif sys.platform == 'win32':
                            if trust_oids != empty_set and any_purpose not in trust_oids \
                                    and win_server_auth not in trust_oids:
                                if cert_callback:
                                    cert_callback(Certificate.load(cert), 'implicitly distrusted for TLS')
                                continue
                            if reject_oids != empty_set and (win_server_auth in reject_oids
                                                             or any_purpose in reject_oids):
                                if cert_callback:
                                    cert_callback(Certificate.load(cert), 'explicitly distrusted for TLS')
                                continue
                        if cert_callback:
                            cert_callback(Certificate.load(cert), None)
                        f.write(armor('CERTIFICATE', cert))

    if not ca_path:
        raise CACertsError('No CA certs found')

    return ca_path


def get_list(cache_length=24, map_vendor_oids=True, cert_callback=None):
    """
    Retrieves (and caches in memory) the list of CA certs from the OS. Includes
    trust information from the OS - purposes the certificate should be trusted
    or rejected for.

    Trust information is encoded via object identifiers (OIDs) that are sourced
    from various RFCs and vendors (Apple and Microsoft). This trust information
    augments what is in the certificate itself. Any OID that is in the set of
    trusted purposes indicates the certificate has been explicitly trusted for
    a purpose beyond the extended key purpose extension. Any OID in the reject
    set is a purpose that the certificate should not be trusted for, even if
    present in the extended key purpose extension.

    *A list of common trust OIDs can be found as part of the `KeyPurposeId()`
    class in the `asn1crypto.x509` module of the `asn1crypto` package.*

    :param cache_length:
        The number of hours to cache the CA certs in memory before they are
        refreshed

    :param map_vendor_oids:
        A bool indicating if the following mapping of OIDs should happen for
        trust information from the OS trust list:
         - 1.2.840.113635.100.1.3 (apple_ssl) -> 1.3.6.1.5.5.7.3.1 (server_auth)
         - 1.2.840.113635.100.1.3 (apple_ssl) -> 1.3.6.1.5.5.7.3.2 (client_auth)
         - 1.2.840.113635.100.1.8 (apple_smime) -> 1.3.6.1.5.5.7.3.4 (email_protection)
         - 1.2.840.113635.100.1.9 (apple_eap) -> 1.3.6.1.5.5.7.3.13 (eap_over_ppp)
         - 1.2.840.113635.100.1.9 (apple_eap) -> 1.3.6.1.5.5.7.3.14 (eap_over_lan)
         - 1.2.840.113635.100.1.11 (apple_ipsec) -> 1.3.6.1.5.5.7.3.5 (ipsec_end_system)
         - 1.2.840.113635.100.1.11 (apple_ipsec) -> 1.3.6.1.5.5.7.3.6 (ipsec_tunnel)
         - 1.2.840.113635.100.1.11 (apple_ipsec) -> 1.3.6.1.5.5.7.3.7 (ipsec_user)
         - 1.2.840.113635.100.1.11 (apple_ipsec) -> 1.3.6.1.5.5.7.3.17 (ipsec_ike)
         - 1.2.840.113635.100.1.16 (apple_code_signing) -> 1.3.6.1.5.5.7.3.3 (code_signing)
         - 1.2.840.113635.100.1.20 (apple_time_stamping) -> 1.3.6.1.5.5.7.3.8 (time_stamping)
         - 1.3.6.1.4.1.311.10.3.2 (microsoft_time_stamp_signing) -> 1.3.6.1.5.5.7.3.8 (time_stamping)

    :param cert_callback:
        A callback that is called once for each certificate in the trust store.
        It should accept two parameters: an asn1crypto.x509.Certificate object,
        and a reason. The reason will be None if the certificate is being
        exported, otherwise it will be a unicode string of the reason it won't.

    :raises:
        oscrypto.errors.CACertsError - when an error occurs exporting/locating certs

    :return:
        A (copied) list of 3-element tuples containing CA certs from the OS
        trust ilst:
         - 0: an asn1crypto.x509.Certificate object
         - 1: a set of unicode strings of OIDs of trusted purposes
         - 2: a set of unicode strings of OIDs of rejected purposes
    """

    if not _in_memory_up_to_date(cache_length):
        with memory_lock:
            if not _in_memory_up_to_date(cache_length):
                certs = []
                for cert_bytes, trust_oids, reject_oids in extract_from_system(cert_callback):
                    if map_vendor_oids:
                        trust_oids = _map_oids(trust_oids)
                        reject_oids = _map_oids(reject_oids)
                    certs.append((Certificate.load(cert_bytes), trust_oids, reject_oids))
                _module_values['certs'] = certs
                _module_values['last_update'] = time.time()

    return list(_module_values['certs'])


def clear_cache(temp_dir=None):
    """
    Clears any cached info that was exported from the OS trust store. This will
    ensure the latest changes are returned from calls to get_list() and
    get_path(), but at the expense of re-exporting and parsing all certificates.

    :param temp_dir:
        The temporary directory to cache the CA certs in on OS X and Windows.
        Needs to have secure permissions so other users can not modify the
        contents. Must be the same value passed to get_path().
    """

    with memory_lock:
        _module_values['last_update'] = None
        _module_values['certs'] = None

    ca_path, temp = _ca_path(temp_dir)
    if temp:
        with path_lock:
            if os.path.exists(ca_path):
                os.remove(ca_path)


def _ca_path(temp_dir=None):
    """
    Returns the file path to the CA certs file

    :param temp_dir:
        The temporary directory to cache the CA certs in on OS X and Windows.
        Needs to have secure permissions so other users can not modify the
        contents.

    :return:
        A 2-element tuple:
         - 0: A unicode string of the file path
         - 1: A bool if the file is a temporary file
    """

    ca_path = system_path()

    # Windows and OS X
    if ca_path is None:
        if temp_dir is None:
            temp_dir = tempfile.gettempdir()

        if not os.path.isdir(temp_dir):
            raise CACertsError(pretty_message(
                '''
                The temp dir specified, "%s", is not a directory
                ''',
                temp_dir
            ))

        ca_path = os.path.join(temp_dir, 'oscrypto-ca-bundle.crt')
        return (ca_path, True)

    return (ca_path, False)


def _map_oids(oids):
    """
    Takes a set of unicode string OIDs and converts vendor-specific OIDs into
    generics OIDs from RFCs.

     - 1.2.840.113635.100.1.3 (apple_ssl) -> 1.3.6.1.5.5.7.3.1 (server_auth)
     - 1.2.840.113635.100.1.3 (apple_ssl) -> 1.3.6.1.5.5.7.3.2 (client_auth)
     - 1.2.840.113635.100.1.8 (apple_smime) -> 1.3.6.1.5.5.7.3.4 (email_protection)
     - 1.2.840.113635.100.1.9 (apple_eap) -> 1.3.6.1.5.5.7.3.13 (eap_over_ppp)
     - 1.2.840.113635.100.1.9 (apple_eap) -> 1.3.6.1.5.5.7.3.14 (eap_over_lan)
     - 1.2.840.113635.100.1.11 (apple_ipsec) -> 1.3.6.1.5.5.7.3.5 (ipsec_end_system)
     - 1.2.840.113635.100.1.11 (apple_ipsec) -> 1.3.6.1.5.5.7.3.6 (ipsec_tunnel)
     - 1.2.840.113635.100.1.11 (apple_ipsec) -> 1.3.6.1.5.5.7.3.7 (ipsec_user)
     - 1.2.840.113635.100.1.11 (apple_ipsec) -> 1.3.6.1.5.5.7.3.17 (ipsec_ike)
     - 1.2.840.113635.100.1.16 (apple_code_signing) -> 1.3.6.1.5.5.7.3.3 (code_signing)
     - 1.2.840.113635.100.1.20 (apple_time_stamping) -> 1.3.6.1.5.5.7.3.8 (time_stamping)
     - 1.3.6.1.4.1.311.10.3.2 (microsoft_time_stamp_signing) -> 1.3.6.1.5.5.7.3.8 (time_stamping)

    :param oids:
        A set of unicode strings

    :return:
        The original set of OIDs with any mapped OIDs added
    """

    new_oids = set()
    for oid in oids:
        if oid in _oid_map:
            new_oids |= _oid_map[oid]
    return oids | new_oids


def _cached_path_needs_update(ca_path, cache_length):
    """
    Checks to see if a cache file needs to be refreshed

    :param ca_path:
        A unicode string of the path to the cache file

    :param cache_length:
        An integer representing the number of hours the cache is valid for

    :return:
        A boolean - True if the cache needs to be updated, False if the file
        is up-to-date
    """

    exists = os.path.exists(ca_path)
    if not exists:
        return True

    stats = os.stat(ca_path)

    if stats.st_mtime < time.time() - cache_length * 60 * 60:
        return True

    if stats.st_size == 0:
        return True

    return False


def _in_memory_up_to_date(cache_length):
    """
    Checks to see if the in-memory cache of certificates is fresh

    :param cache_length:
        An integer representing the number of hours the cache is valid for

    :return:
        A boolean - True if the cache is up-to-date, False if it needs to be
        refreshed
    """

    return (
        _module_values['certs'] and
        _module_values['last_update'] and
        _module_values['last_update'] > time.time() - (cache_length * 60 * 60)
    )
