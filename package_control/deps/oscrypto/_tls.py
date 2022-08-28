# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import re
from datetime import datetime

from ._asn1 import Certificate, int_from_bytes, timezone
from ._cipher_suites import CIPHER_SUITE_MAP
from .errors import TLSVerificationError, TLSDisconnectError, TLSError


__all__ = [
    'detect_client_auth_request',
    'extract_chain',
    'get_dh_params_length',
    'parse_alert',
    'parse_handshake_messages',
    'parse_session_info',
    'parse_tls_records',
    'raise_client_auth',
    'raise_dh_params',
    'raise_disconnection',
    'raise_expired_not_yet_valid',
    'raise_handshake',
    'raise_hostname',
    'raise_no_issuer',
    'raise_protocol_error',
    'raise_revoked',
    'raise_self_signed',
    'raise_verification',
    'raise_weak_signature',
]


def extract_chain(server_handshake_bytes):
    """
    Extracts the X.509 certificates from the server handshake bytes for use
    when debugging

    :param server_handshake_bytes:
        A byte string of the handshake data received from the server

    :return:
        A list of asn1crypto.x509.Certificate objects
    """

    output = []

    chain_bytes = None

    for record_type, _, record_data in parse_tls_records(server_handshake_bytes):
        if record_type != b'\x16':
            continue
        for message_type, message_data in parse_handshake_messages(record_data):
            if message_type == b'\x0b':
                chain_bytes = message_data
                break
        if chain_bytes:
            break

    if chain_bytes:
        # The first 3 bytes are the cert chain length
        pointer = 3
        while pointer < len(chain_bytes):
            cert_length = int_from_bytes(chain_bytes[pointer:pointer + 3])
            cert_start = pointer + 3
            cert_end = cert_start + cert_length
            pointer = cert_end
            cert_bytes = chain_bytes[cert_start:cert_end]
            output.append(Certificate.load(cert_bytes))

    return output


def detect_client_auth_request(server_handshake_bytes):
    """
    Determines if a CertificateRequest message is sent from the server asking
    the client for a certificate

    :param server_handshake_bytes:
        A byte string of the handshake data received from the server

    :return:
        A boolean - if a client certificate request was found
    """

    for record_type, _, record_data in parse_tls_records(server_handshake_bytes):
        if record_type != b'\x16':
            continue
        for message_type, message_data in parse_handshake_messages(record_data):
            if message_type == b'\x0d':
                return True
    return False


def get_dh_params_length(server_handshake_bytes):
    """
    Determines the length of the DH params from the ServerKeyExchange

    :param server_handshake_bytes:
        A byte string of the handshake data received from the server

    :return:
        None or an integer of the bit size of the DH parameters
    """

    output = None

    dh_params_bytes = None

    for record_type, _, record_data in parse_tls_records(server_handshake_bytes):
        if record_type != b'\x16':
            continue
        for message_type, message_data in parse_handshake_messages(record_data):
            if message_type == b'\x0c':
                dh_params_bytes = message_data
                break
        if dh_params_bytes:
            break

    if dh_params_bytes:
        output = int_from_bytes(dh_params_bytes[0:2]) * 8

    return output


def parse_alert(server_handshake_bytes):
    """
    Parses the handshake for protocol alerts

    :param server_handshake_bytes:
        A byte string of the handshake data received from the server

    :return:
        None or an 2-element tuple of integers:
         0: 1 (warning) or 2 (fatal)
         1: The alert description (see https://tools.ietf.org/html/rfc5246#section-7.2)
    """

    for record_type, _, record_data in parse_tls_records(server_handshake_bytes):
        if record_type != b'\x15':
            continue
        if len(record_data) != 2:
            return None
        return (int_from_bytes(record_data[0:1]), int_from_bytes(record_data[1:2]))
    return None


def parse_session_info(server_handshake_bytes, client_handshake_bytes):
    """
    Parse the TLS handshake from the client to the server to extract information
    including the cipher suite selected, if compression is enabled, the
    session id and if a new or reused session ticket exists.

    :param server_handshake_bytes:
        A byte string of the handshake data received from the server

    :param client_handshake_bytes:
        A byte string of the handshake data sent to the server

    :return:
        A dict with the following keys:
         - "protocol": unicode string
         - "cipher_suite": unicode string
         - "compression": boolean
         - "session_id": "new", "reused" or None
         - "session_ticket: "new", "reused" or None
    """

    protocol = None
    cipher_suite = None
    compression = False
    session_id = None
    session_ticket = None

    server_session_id = None
    client_session_id = None

    for record_type, _, record_data in parse_tls_records(server_handshake_bytes):
        if record_type != b'\x16':
            continue
        for message_type, message_data in parse_handshake_messages(record_data):
            # Ensure we are working with a ServerHello message
            if message_type != b'\x02':
                continue
            protocol = {
                b'\x03\x00': "SSLv3",
                b'\x03\x01': "TLSv1",
                b'\x03\x02': "TLSv1.1",
                b'\x03\x03': "TLSv1.2",
                b'\x03\x04': "TLSv1.3",
            }[message_data[0:2]]

            session_id_length = int_from_bytes(message_data[34:35])
            if session_id_length > 0:
                server_session_id = message_data[35:35 + session_id_length]

            cipher_suite_start = 35 + session_id_length
            cipher_suite_bytes = message_data[cipher_suite_start:cipher_suite_start + 2]
            cipher_suite = CIPHER_SUITE_MAP[cipher_suite_bytes]

            compression_start = cipher_suite_start + 2
            compression = message_data[compression_start:compression_start + 1] != b'\x00'

            extensions_length_start = compression_start + 1
            extensions_data = message_data[extensions_length_start:]
            for extension_type, extension_data in _parse_hello_extensions(extensions_data):
                if extension_type == 35:
                    session_ticket = "new"
                    break
            break

    for record_type, _, record_data in parse_tls_records(client_handshake_bytes):
        if record_type != b'\x16':
            continue
        for message_type, message_data in parse_handshake_messages(record_data):
            # Ensure we are working with a ClientHello message
            if message_type != b'\x01':
                continue

            session_id_length = int_from_bytes(message_data[34:35])
            if session_id_length > 0:
                client_session_id = message_data[35:35 + session_id_length]

            cipher_suite_start = 35 + session_id_length
            cipher_suite_length = int_from_bytes(message_data[cipher_suite_start:cipher_suite_start + 2])

            compression_start = cipher_suite_start + 2 + cipher_suite_length
            compression_length = int_from_bytes(message_data[compression_start:compression_start + 1])

            # On subsequent requests, the session ticket will only be seen
            # in the ClientHello message
            if server_session_id is None and session_ticket is None:
                extensions_length_start = compression_start + 1 + compression_length
                extensions_data = message_data[extensions_length_start:]
                for extension_type, extension_data in _parse_hello_extensions(extensions_data):
                    if extension_type == 35:
                        session_ticket = "reused"
                        break
            break

    if server_session_id is not None:
        if client_session_id is None:
            session_id = "new"
        else:
            if client_session_id != server_session_id:
                session_id = "new"
            else:
                session_id = "reused"

    return {
        "protocol": protocol,
        "cipher_suite": cipher_suite,
        "compression": compression,
        "session_id": session_id,
        "session_ticket": session_ticket,
    }


def parse_tls_records(data):
    """
    Creates a generator returning tuples of information about each record
    in a byte string of data from a TLS client or server. Stops as soon as it
    find a ChangeCipherSpec message since all data from then on is encrypted.

    :param data:
        A byte string of TLS records

    :return:
        A generator that yields 3-element tuples:
        [0] Byte string of record type
        [1] Byte string of protocol version
        [2] Byte string of record data
    """

    pointer = 0
    data_len = len(data)
    while pointer < data_len:
        # Don't try to parse any more once the ChangeCipherSpec is found
        if data[pointer:pointer + 1] == b'\x14':
            break
        length = int_from_bytes(data[pointer + 3:pointer + 5])
        yield (
            data[pointer:pointer + 1],
            data[pointer + 1:pointer + 3],
            data[pointer + 5:pointer + 5 + length]
        )
        pointer += 5 + length


def parse_handshake_messages(data):
    """
    Creates a generator returning tuples of information about each message in
    a byte string of data from a TLS handshake record

    :param data:
        A byte string of a TLS handshake record data

    :return:
        A generator that yields 2-element tuples:
        [0] Byte string of message type
        [1] Byte string of message data
    """

    pointer = 0
    data_len = len(data)
    while pointer < data_len:
        length = int_from_bytes(data[pointer + 1:pointer + 4])
        yield (
            data[pointer:pointer + 1],
            data[pointer + 4:pointer + 4 + length]
        )
        pointer += 4 + length


def _parse_hello_extensions(data):
    """
    Creates a generator returning tuples of information about each extension
    from a byte string of extension data contained in a ServerHello ores
    ClientHello message

    :param data:
        A byte string of a extension data from a TLS ServerHello or ClientHello
        message

    :return:
        A generator that yields 2-element tuples:
        [0] Byte string of extension type
        [1] Byte string of extension data
    """

    if data == b'':
        return

    extentions_length = int_from_bytes(data[0:2])
    extensions_start = 2
    extensions_end = 2 + extentions_length

    pointer = extensions_start
    while pointer < extensions_end:
        extension_type = int_from_bytes(data[pointer:pointer + 2])
        extension_length = int_from_bytes(data[pointer + 2:pointer + 4])
        yield (
            extension_type,
            data[pointer + 4:pointer + 4 + extension_length]
        )
        pointer += 4 + extension_length


def raise_hostname(certificate, hostname):
    """
    Raises a TLSVerificationError due to a hostname mismatch

    :param certificate:
        An asn1crypto.x509.Certificate object

    :raises:
        TLSVerificationError
    """

    is_ip = re.match('^\\d+\\.\\d+\\.\\d+\\.\\d+$', hostname) or hostname.find(':') != -1
    if is_ip:
        hostname_type = 'IP address %s' % hostname
    else:
        hostname_type = 'domain name %s' % hostname
    message = 'Server certificate verification failed - %s does not match' % hostname_type
    valid_ips = ', '.join(certificate.valid_ips)
    valid_domains = ', '.join(certificate.valid_domains)
    if valid_domains:
        message += ' valid domains: %s' % valid_domains
    if valid_domains and valid_ips:
        message += ' or'
    if valid_ips:
        message += ' valid IP addresses: %s' % valid_ips
    raise TLSVerificationError(message, certificate)


def raise_verification(certificate):
    """
    Raises a generic TLSVerificationError

    :param certificate:
        An asn1crypto.x509.Certificate object

    :raises:
        TLSVerificationError
    """

    message = 'Server certificate verification failed'
    raise TLSVerificationError(message, certificate)


def raise_weak_signature(certificate):
    """
    Raises a TLSVerificationError when a certificate uses a weak signature
    algorithm

    :param certificate:
        An asn1crypto.x509.Certificate object

    :raises:
        TLSVerificationError
    """

    message = 'Server certificate verification failed - weak certificate signature algorithm'
    raise TLSVerificationError(message, certificate)


def raise_client_auth():
    """
    Raises a TLSError indicating client authentication is required

    :raises:
        TLSError
    """

    message = 'TLS handshake failed - client authentication required'
    raise TLSError(message)


def raise_revoked(certificate):
    """
    Raises a TLSVerificationError due to the certificate being revoked

    :param certificate:
        An asn1crypto.x509.Certificate object

    :raises:
        TLSVerificationError
    """

    message = 'Server certificate verification failed - certificate has been revoked'
    raise TLSVerificationError(message, certificate)


def raise_no_issuer(certificate):
    """
    Raises a TLSVerificationError due to no issuer certificate found in trust
    roots

    :param certificate:
        An asn1crypto.x509.Certificate object

    :raises:
        TLSVerificationError
    """

    message = 'Server certificate verification failed - certificate issuer not found in trusted root certificate store'
    raise TLSVerificationError(message, certificate)


def raise_self_signed(certificate):
    """
    Raises a TLSVerificationError due to a self-signed certificate
    roots

    :param certificate:
        An asn1crypto.x509.Certificate object

    :raises:
        TLSVerificationError
    """

    message = 'Server certificate verification failed - certificate is self-signed'
    raise TLSVerificationError(message, certificate)


def raise_lifetime_too_long(certificate):
    """
    Raises a TLSVerificationError due to a certificate lifetime exceeding
    the CAB forum certificate lifetime limit

    :param certificate:
        An asn1crypto.x509.Certificate object

    :raises:
        TLSVerificationError
    """

    message = 'Server certificate verification failed - certificate lifetime is too long'
    raise TLSVerificationError(message, certificate)


def raise_expired_not_yet_valid(certificate):
    """
    Raises a TLSVerificationError due to certificate being expired, or not yet
    being valid

    :param certificate:
        An asn1crypto.x509.Certificate object

    :raises:
        TLSVerificationError
    """

    validity = certificate['tbs_certificate']['validity']
    not_after = validity['not_after'].native
    not_before = validity['not_before'].native

    now = datetime.now(timezone.utc)

    if not_before > now:
        formatted_before = not_before.strftime('%Y-%m-%d %H:%M:%SZ')
        message = 'Server certificate verification failed - certificate not valid until %s' % formatted_before
    elif not_after < now:
        formatted_after = not_after.strftime('%Y-%m-%d %H:%M:%SZ')
        message = 'Server certificate verification failed - certificate expired %s' % formatted_after

    raise TLSVerificationError(message, certificate)


def raise_disconnection():
    """
    Raises a TLSDisconnectError due to a disconnection

    :raises:
        TLSDisconnectError
    """

    raise TLSDisconnectError('The remote end closed the connection')


def raise_protocol_error(server_handshake_bytes):
    """
    Raises a TLSError due to a protocol error

    :param server_handshake_bytes:
        A byte string of the handshake data received from the server

    :raises:
        TLSError
    """

    other_protocol = detect_other_protocol(server_handshake_bytes)

    if other_protocol:
        raise TLSError('TLS protocol error - server responded using %s' % other_protocol)

    raise TLSError('TLS protocol error - server responded using a different protocol')


def raise_handshake():
    """
    Raises a TLSError due to a handshake error

    :raises:
        TLSError
    """

    raise TLSError('TLS handshake failed')


def raise_protocol_version():
    """
    Raises a TLSError due to a TLS version incompatibility

    :raises:
        TLSError
    """

    raise TLSError('TLS handshake failed - protocol version error')


def raise_dh_params():
    """
    Raises a TLSError due to weak DH params

    :raises:
        TLSError
    """

    raise TLSError('TLS handshake failed - weak DH parameters')


def detect_other_protocol(server_handshake_bytes):
    """
    Looks at the server handshake bytes to try and detect a different protocol

    :param server_handshake_bytes:
        A byte string of the handshake data received from the server

    :return:
        None, or a unicode string of "ftp", "http", "imap", "pop3", "smtp"
    """

    if server_handshake_bytes[0:5] == b'HTTP/':
        return 'HTTP'

    if server_handshake_bytes[0:4] == b'220 ':
        if re.match(b'^[^\r\n]*ftp', server_handshake_bytes, re.I):
            return 'FTP'
        else:
            return 'SMTP'

    if server_handshake_bytes[0:4] == b'220-':
        return 'FTP'

    if server_handshake_bytes[0:4] == b'+OK ':
        return 'POP3'

    if server_handshake_bytes[0:4] == b'* OK' or server_handshake_bytes[0:9] == b'* PREAUTH':
        return 'IMAP'

    return None
