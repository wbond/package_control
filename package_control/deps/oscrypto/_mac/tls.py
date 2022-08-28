# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import datetime
import sys
import re
import socket as socket_
import select
import numbers
import errno
import weakref

from ._security import Security, osx_version_info, handle_sec_error, SecurityConst
from ._core_foundation import CoreFoundation, handle_cf_error, CFHelpers
from .._asn1 import (
    Certificate as Asn1Certificate,
    int_to_bytes,
    timezone,
)
from .._errors import pretty_message
from .._ffi import (
    array_from_pointer,
    array_set,
    buffer_from_bytes,
    bytes_from_buffer,
    callback,
    cast,
    deref,
    new,
    null,
    pointer_set,
    struct,
    struct_bytes,
    unwrap,
    write_to_buffer,
)
from .._types import type_name, str_cls, byte_cls, int_types
from .._cipher_suites import CIPHER_SUITE_MAP
from .util import rand_bytes
from ..errors import TLSError, TLSDisconnectError, TLSGracefulDisconnectError
from .._tls import (
    detect_client_auth_request,
    detect_other_protocol,
    extract_chain,
    get_dh_params_length,
    parse_session_info,
    raise_client_auth,
    raise_dh_params,
    raise_disconnection,
    raise_expired_not_yet_valid,
    raise_handshake,
    raise_hostname,
    raise_lifetime_too_long,
    raise_no_issuer,
    raise_protocol_error,
    raise_protocol_version,
    raise_revoked,
    raise_self_signed,
    raise_verification,
    raise_weak_signature,
)
from .asymmetric import load_certificate, Certificate
from ..keys import parse_certificate

if sys.version_info < (3,):
    range = xrange  # noqa

if sys.version_info < (3, 7):
    Pattern = re._pattern_type
else:
    Pattern = re.Pattern


__all__ = [
    'TLSSession',
    'TLSSocket',
]


_PROTOCOL_STRING_CONST_MAP = {
    'SSLv2': SecurityConst.kSSLProtocol2,
    'SSLv3': SecurityConst.kSSLProtocol3,
    'TLSv1': SecurityConst.kTLSProtocol1,
    'TLSv1.1': SecurityConst.kTLSProtocol11,
    'TLSv1.2': SecurityConst.kTLSProtocol12,
}

_PROTOCOL_CONST_STRING_MAP = {
    SecurityConst.kSSLProtocol2: 'SSLv2',
    SecurityConst.kSSLProtocol3: 'SSLv3',
    SecurityConst.kTLSProtocol1: 'TLSv1',
    SecurityConst.kTLSProtocol11: 'TLSv1.1',
    SecurityConst.kTLSProtocol12: 'TLSv1.2',
}

_line_regex = re.compile(b'(\r\n|\r|\n)')
_cipher_blacklist_regex = re.compile('anon|PSK|SEED|RC4|MD5|NULL|CAMELLIA|ARIA|SRP|KRB5|EXPORT|(?<!3)DES|IDEA')
_connection_refs = weakref.WeakValueDictionary()
_socket_refs = {}


def _read_callback(connection_id, data_buffer, data_length_pointer):
    """
    Callback called by Secure Transport to actually read the socket

    :param connection_id:
        An integer identifying the connection

    :param data_buffer:
        A char pointer FFI type to write the data to

    :param data_length_pointer:
        A size_t pointer FFI type of the amount of data to read. Will be
        overwritten with the amount of data read on return.

    :return:
        An integer status code of the result - 0 for success
    """

    self = None
    try:
        self = _connection_refs.get(connection_id)
        if not self:
            socket = _socket_refs.get(connection_id)
        else:
            socket = self._socket

        if not self and not socket:
            return 0

        bytes_requested = deref(data_length_pointer)

        timeout = socket.gettimeout()
        error = None
        data = b''
        try:
            while len(data) < bytes_requested:
                # Python 2 on Travis CI seems to have issues with blocking on
                # recv() for longer than the socket timeout value, so we select
                if timeout is not None and timeout > 0.0:
                    read_ready, _, _ = select.select([socket], [], [], timeout)
                    if len(read_ready) == 0:
                        raise socket_.error(errno.EAGAIN, 'timed out')
                chunk = socket.recv(bytes_requested - len(data))
                data += chunk
                if chunk == b'':
                    if len(data) == 0:
                        if timeout is None:
                            return SecurityConst.errSSLClosedNoNotify
                        return SecurityConst.errSSLClosedAbort
                    break
        except (socket_.error) as e:
            error = e.errno

        if error is not None and error != errno.EAGAIN:
            if error == errno.ECONNRESET or error == errno.EPIPE:
                return SecurityConst.errSSLClosedNoNotify
            return SecurityConst.errSSLClosedAbort

        if self and not self._done_handshake:
            # SecureTransport doesn't bother to check if the TLS record header
            # is valid before asking to read more data, which can result in
            # connection hangs. Here we do basic checks to get around the issue.
            if len(data) >= 3 and len(self._server_hello) == 0:
                # Check to ensure it is an alert or handshake first
                valid_record_type = data[0:1] in set([b'\x15', b'\x16'])
                # Check if the protocol version is SSL 3.0 or TLS 1.0-1.3
                valid_protocol_version = data[1:3] in set([
                    b'\x03\x00',
                    b'\x03\x01',
                    b'\x03\x02',
                    b'\x03\x03',
                    b'\x03\x04'
                ])
                if not valid_record_type or not valid_protocol_version:
                    self._server_hello += data + _read_remaining(socket)
                    return SecurityConst.errSSLProtocol
            self._server_hello += data

        write_to_buffer(data_buffer, data)
        pointer_set(data_length_pointer, len(data))

        if len(data) != bytes_requested:
            return SecurityConst.errSSLWouldBlock

        return 0
    except (KeyboardInterrupt) as e:
        if self:
            self._exception = e
        return SecurityConst.errSSLClosedAbort


def _read_remaining(socket):
    """
    Reads everything available from the socket - used for debugging when there
    is a protocol error

    :param socket:
        The socket to read from

    :return:
        A byte string of the remaining data
    """

    output = b''
    old_timeout = socket.gettimeout()
    try:
        socket.settimeout(0.0)
        output += socket.recv(8192)
    except (socket_.error):
        pass
    finally:
        socket.settimeout(old_timeout)
    return output


def _write_callback(connection_id, data_buffer, data_length_pointer):
    """
    Callback called by Secure Transport to actually write to the socket

    :param connection_id:
        An integer identifying the connection

    :param data_buffer:
        A char pointer FFI type containing the data to write

    :param data_length_pointer:
        A size_t pointer FFI type of the amount of data to write. Will be
        overwritten with the amount of data actually written on return.

    :return:
        An integer status code of the result - 0 for success
    """

    try:
        self = _connection_refs.get(connection_id)
        if not self:
            socket = _socket_refs.get(connection_id)
        else:
            socket = self._socket

        if not self and not socket:
            return 0

        data_length = deref(data_length_pointer)
        data = bytes_from_buffer(data_buffer, data_length)

        if self and not self._done_handshake:
            self._client_hello += data

        error = None
        try:
            sent = socket.send(data)
        except (socket_.error) as e:
            error = e.errno

        if error is not None and error != errno.EAGAIN:
            if error == errno.ECONNRESET or error == errno.EPIPE:
                return SecurityConst.errSSLClosedNoNotify
            return SecurityConst.errSSLClosedAbort

        if sent != data_length:
            pointer_set(data_length_pointer, sent)
            return SecurityConst.errSSLWouldBlock

        return 0
    except (KeyboardInterrupt) as e:
        self._exception = e
        return SecurityConst.errSSLPeerUserCancelled


_read_callback_pointer = callback(Security, 'SSLReadFunc', _read_callback)
_write_callback_pointer = callback(Security, 'SSLWriteFunc', _write_callback)


class TLSSession(object):
    """
    A TLS session object that multiple TLSSocket objects can share for the
    sake of session reuse
    """

    _protocols = None
    _ciphers = None
    _manual_validation = None
    _extra_trust_roots = None
    _peer_id = None

    def __init__(self, protocol=None, manual_validation=False, extra_trust_roots=None):
        """
        :param protocol:
            A unicode string or set of unicode strings representing allowable
            protocols to negotiate with the server:

             - "TLSv1.2"
             - "TLSv1.1"
             - "TLSv1"
             - "SSLv3"

            Default is: {"TLSv1", "TLSv1.1", "TLSv1.2"}

        :param manual_validation:
            If certificate and certificate path validation should be skipped
            and left to the developer to implement

        :param extra_trust_roots:
            A list containing one or more certificates to be treated as trust
            roots, in one of the following formats:
             - A byte string of the DER encoded certificate
             - A unicode string of the certificate filename
             - An asn1crypto.x509.Certificate object
             - An oscrypto.asymmetric.Certificate object

        :raises:
            ValueError - when any of the parameters contain an invalid value
            TypeError - when any of the parameters are of the wrong type
            OSError - when an error is returned by the OS crypto library
        """

        if not isinstance(manual_validation, bool):
            raise TypeError(pretty_message(
                '''
                manual_validation must be a boolean, not %s
                ''',
                type_name(manual_validation)
            ))

        self._manual_validation = manual_validation

        if protocol is None:
            protocol = set(['TLSv1', 'TLSv1.1', 'TLSv1.2'])

        if isinstance(protocol, str_cls):
            protocol = set([protocol])
        elif not isinstance(protocol, set):
            raise TypeError(pretty_message(
                '''
                protocol must be a unicode string or set of unicode strings,
                not %s
                ''',
                type_name(protocol)
            ))

        unsupported_protocols = protocol - set(['SSLv3', 'TLSv1', 'TLSv1.1', 'TLSv1.2'])
        if unsupported_protocols:
            raise ValueError(pretty_message(
                '''
                protocol must contain only the unicode strings "SSLv3", "TLSv1",
                "TLSv1.1", "TLSv1.2", not %s
                ''',
                repr(unsupported_protocols)
            ))

        self._protocols = protocol

        self._extra_trust_roots = []
        if extra_trust_roots:
            for extra_trust_root in extra_trust_roots:
                if isinstance(extra_trust_root, Certificate):
                    extra_trust_root = extra_trust_root.asn1
                elif isinstance(extra_trust_root, byte_cls):
                    extra_trust_root = parse_certificate(extra_trust_root)
                elif isinstance(extra_trust_root, str_cls):
                    with open(extra_trust_root, 'rb') as f:
                        extra_trust_root = parse_certificate(f.read())
                elif not isinstance(extra_trust_root, Asn1Certificate):
                    raise TypeError(pretty_message(
                        '''
                        extra_trust_roots must be a list of byte strings, unicode
                        strings, asn1crypto.x509.Certificate objects or
                        oscrypto.asymmetric.Certificate objects, not %s
                        ''',
                        type_name(extra_trust_root)
                    ))
                self._extra_trust_roots.append(extra_trust_root)

        self._peer_id = rand_bytes(8)


class TLSSocket(object):
    """
    A wrapper around a socket.socket that adds TLS
    """

    _socket = None
    _session = None
    _exception = None

    _session_context = None

    _decrypted_bytes = None

    _hostname = None

    _certificate = None
    _intermediates = None

    _protocol = None
    _cipher_suite = None
    _compression = None
    _session_id = None
    _session_ticket = None

    _done_handshake = None
    _server_hello = None
    _client_hello = None

    _local_closed = False
    _gracefully_closed = False

    _connection_id = None

    @classmethod
    def wrap(cls, socket, hostname, session=None):
        """
        Takes an existing socket and adds TLS

        :param socket:
            A socket.socket object to wrap with TLS

        :param hostname:
            A unicode string of the hostname or IP the socket is connected to

        :param session:
            An existing TLSSession object to allow for session reuse, specific
            protocol or manual certificate validation

        :raises:
            ValueError - when any of the parameters contain an invalid value
            TypeError - when any of the parameters are of the wrong type
            OSError - when an error is returned by the OS crypto library
        """

        if not isinstance(socket, socket_.socket):
            raise TypeError(pretty_message(
                '''
                socket must be an instance of socket.socket, not %s
                ''',
                type_name(socket)
            ))

        if not isinstance(hostname, str_cls):
            raise TypeError(pretty_message(
                '''
                hostname must be a unicode string, not %s
                ''',
                type_name(hostname)
            ))

        if session is not None and not isinstance(session, TLSSession):
            raise TypeError(pretty_message(
                '''
                session must be an instance of oscrypto.tls.TLSSession, not %s
                ''',
                type_name(session)
            ))

        new_socket = cls(None, None, session=session)
        new_socket._socket = socket
        new_socket._hostname = hostname
        new_socket._handshake()

        return new_socket

    def __init__(self, address, port, timeout=10, session=None):
        """
        :param address:
            A unicode string of the domain name or IP address to connect to

        :param port:
            An integer of the port number to connect to

        :param timeout:
            An integer timeout to use for the socket

        :param session:
            An oscrypto.tls.TLSSession object to allow for session reuse and
            controlling the protocols and validation performed
        """

        self._done_handshake = False
        self._server_hello = b''
        self._client_hello = b''

        self._decrypted_bytes = b''

        if address is None and port is None:
            self._socket = None

        else:
            if not isinstance(address, str_cls):
                raise TypeError(pretty_message(
                    '''
                    address must be a unicode string, not %s
                    ''',
                    type_name(address)
                ))

            if not isinstance(port, int_types):
                raise TypeError(pretty_message(
                    '''
                    port must be an integer, not %s
                    ''',
                    type_name(port)
                ))

            if timeout is not None and not isinstance(timeout, numbers.Number):
                raise TypeError(pretty_message(
                    '''
                    timeout must be a number, not %s
                    ''',
                    type_name(timeout)
                ))

            self._socket = socket_.create_connection((address, port), timeout)
            self._socket.settimeout(timeout)

        if session is None:
            session = TLSSession()

        elif not isinstance(session, TLSSession):
            raise TypeError(pretty_message(
                '''
                session must be an instance of oscrypto.tls.TLSSession, not %s
                ''',
                type_name(session)
            ))

        self._session = session

        if self._socket:
            self._hostname = address
            self._handshake()

    def _handshake(self):
        """
        Perform an initial TLS handshake
        """

        session_context = None
        ssl_policy_ref = None
        crl_search_ref = None
        crl_policy_ref = None
        ocsp_search_ref = None
        ocsp_policy_ref = None
        policy_array_ref = None
        trust_ref = None

        try:
            if osx_version_info < (10, 8):
                session_context_pointer = new(Security, 'SSLContextRef *')
                result = Security.SSLNewContext(False, session_context_pointer)
                handle_sec_error(result)
                session_context = unwrap(session_context_pointer)

            else:
                session_context = Security.SSLCreateContext(
                    null(),
                    SecurityConst.kSSLClientSide,
                    SecurityConst.kSSLStreamType
                )

            result = Security.SSLSetIOFuncs(
                session_context,
                _read_callback_pointer,
                _write_callback_pointer
            )
            handle_sec_error(result)

            self._connection_id = id(self) % 2147483647
            _connection_refs[self._connection_id] = self
            _socket_refs[self._connection_id] = self._socket
            result = Security.SSLSetConnection(session_context, self._connection_id)
            handle_sec_error(result)

            utf8_domain = self._hostname.encode('utf-8')
            result = Security.SSLSetPeerDomainName(
                session_context,
                utf8_domain,
                len(utf8_domain)
            )
            handle_sec_error(result)

            if osx_version_info >= (10, 10):
                disable_auto_validation = self._session._manual_validation or self._session._extra_trust_roots
                explicit_validation = (not self._session._manual_validation) and self._session._extra_trust_roots
            else:
                disable_auto_validation = True
                explicit_validation = not self._session._manual_validation

            # Ensure requested protocol support is set for the session
            if osx_version_info < (10, 8):
                for protocol in ['SSLv2', 'SSLv3', 'TLSv1']:
                    protocol_const = _PROTOCOL_STRING_CONST_MAP[protocol]
                    enabled = protocol in self._session._protocols
                    result = Security.SSLSetProtocolVersionEnabled(
                        session_context,
                        protocol_const,
                        enabled
                    )
                    handle_sec_error(result)

                if disable_auto_validation:
                    result = Security.SSLSetEnableCertVerify(session_context, False)
                    handle_sec_error(result)

            else:
                protocol_consts = [_PROTOCOL_STRING_CONST_MAP[protocol] for protocol in self._session._protocols]
                min_protocol = min(protocol_consts)
                max_protocol = max(protocol_consts)
                result = Security.SSLSetProtocolVersionMin(
                    session_context,
                    min_protocol
                )
                handle_sec_error(result)
                result = Security.SSLSetProtocolVersionMax(
                    session_context,
                    max_protocol
                )
                handle_sec_error(result)

                if disable_auto_validation:
                    result = Security.SSLSetSessionOption(
                        session_context,
                        SecurityConst.kSSLSessionOptionBreakOnServerAuth,
                        True
                    )
                    handle_sec_error(result)

            # Disable all sorts of bad cipher suites
            supported_ciphers_pointer = new(Security, 'size_t *')
            result = Security.SSLGetNumberSupportedCiphers(session_context, supported_ciphers_pointer)
            handle_sec_error(result)

            supported_ciphers = deref(supported_ciphers_pointer)

            cipher_buffer = buffer_from_bytes(supported_ciphers * 4)
            supported_cipher_suites_pointer = cast(Security, 'uint32_t *', cipher_buffer)
            result = Security.SSLGetSupportedCiphers(
                session_context,
                supported_cipher_suites_pointer,
                supported_ciphers_pointer
            )
            handle_sec_error(result)

            supported_ciphers = deref(supported_ciphers_pointer)
            supported_cipher_suites = array_from_pointer(
                Security,
                'uint32_t',
                supported_cipher_suites_pointer,
                supported_ciphers
            )
            good_ciphers = []
            for supported_cipher_suite in supported_cipher_suites:
                cipher_suite = int_to_bytes(supported_cipher_suite, width=2)
                cipher_suite_name = CIPHER_SUITE_MAP.get(cipher_suite, cipher_suite)
                good_cipher = _cipher_blacklist_regex.search(cipher_suite_name) is None
                if good_cipher:
                    good_ciphers.append(supported_cipher_suite)

            num_good_ciphers = len(good_ciphers)
            good_ciphers_array = new(Security, 'uint32_t[]', num_good_ciphers)
            array_set(good_ciphers_array, good_ciphers)
            good_ciphers_pointer = cast(Security, 'uint32_t *', good_ciphers_array)
            result = Security.SSLSetEnabledCiphers(
                session_context,
                good_ciphers_pointer,
                num_good_ciphers
            )
            handle_sec_error(result)

            # Set a peer id from the session to allow for session reuse, the hostname
            # is appended to prevent a bug on OS X 10.7 where it tries to reuse a
            # connection even if the hostnames are different.
            peer_id = self._session._peer_id + self._hostname.encode('utf-8')
            result = Security.SSLSetPeerID(session_context, peer_id, len(peer_id))
            handle_sec_error(result)

            handshake_result = Security.SSLHandshake(session_context)
            if self._exception is not None:
                exception = self._exception
                self._exception = None
                raise exception
            while handshake_result == SecurityConst.errSSLWouldBlock:
                handshake_result = Security.SSLHandshake(session_context)
                if self._exception is not None:
                    exception = self._exception
                    self._exception = None
                    raise exception

            if osx_version_info < (10, 8) and osx_version_info >= (10, 7):
                do_validation = explicit_validation and handshake_result == 0
            else:
                do_validation = explicit_validation and handshake_result == SecurityConst.errSSLServerAuthCompleted

            if do_validation:
                trust_ref_pointer = new(Security, 'SecTrustRef *')
                result = Security.SSLCopyPeerTrust(
                    session_context,
                    trust_ref_pointer
                )
                handle_sec_error(result)
                trust_ref = unwrap(trust_ref_pointer)

                cf_string_hostname = CFHelpers.cf_string_from_unicode(self._hostname)
                ssl_policy_ref = Security.SecPolicyCreateSSL(True, cf_string_hostname)
                result = CoreFoundation.CFRelease(cf_string_hostname)
                handle_cf_error(result)

                # Create a new policy for OCSP checking to disable it
                ocsp_oid_pointer = struct(Security, 'CSSM_OID')
                ocsp_oid = unwrap(ocsp_oid_pointer)
                ocsp_oid.Length = len(SecurityConst.APPLE_TP_REVOCATION_OCSP)
                ocsp_oid_buffer = buffer_from_bytes(SecurityConst.APPLE_TP_REVOCATION_OCSP)
                ocsp_oid.Data = cast(Security, 'char *', ocsp_oid_buffer)

                ocsp_search_ref_pointer = new(Security, 'SecPolicySearchRef *')
                result = Security.SecPolicySearchCreate(
                    SecurityConst.CSSM_CERT_X_509v3,
                    ocsp_oid_pointer,
                    null(),
                    ocsp_search_ref_pointer
                )
                handle_sec_error(result)
                ocsp_search_ref = unwrap(ocsp_search_ref_pointer)

                ocsp_policy_ref_pointer = new(Security, 'SecPolicyRef *')
                result = Security.SecPolicySearchCopyNext(ocsp_search_ref, ocsp_policy_ref_pointer)
                handle_sec_error(result)
                ocsp_policy_ref = unwrap(ocsp_policy_ref_pointer)

                ocsp_struct_pointer = struct(Security, 'CSSM_APPLE_TP_OCSP_OPTIONS')
                ocsp_struct = unwrap(ocsp_struct_pointer)
                ocsp_struct.Version = SecurityConst.CSSM_APPLE_TP_OCSP_OPTS_VERSION
                ocsp_struct.Flags = (
                    SecurityConst.CSSM_TP_ACTION_OCSP_DISABLE_NET |
                    SecurityConst.CSSM_TP_ACTION_OCSP_CACHE_READ_DISABLE
                )
                ocsp_struct_bytes = struct_bytes(ocsp_struct_pointer)

                cssm_data_pointer = struct(Security, 'CSSM_DATA')
                cssm_data = unwrap(cssm_data_pointer)
                cssm_data.Length = len(ocsp_struct_bytes)
                ocsp_struct_buffer = buffer_from_bytes(ocsp_struct_bytes)
                cssm_data.Data = cast(Security, 'char *', ocsp_struct_buffer)

                result = Security.SecPolicySetValue(ocsp_policy_ref, cssm_data_pointer)
                handle_sec_error(result)

                # Create a new policy for CRL checking to disable it
                crl_oid_pointer = struct(Security, 'CSSM_OID')
                crl_oid = unwrap(crl_oid_pointer)
                crl_oid.Length = len(SecurityConst.APPLE_TP_REVOCATION_CRL)
                crl_oid_buffer = buffer_from_bytes(SecurityConst.APPLE_TP_REVOCATION_CRL)
                crl_oid.Data = cast(Security, 'char *', crl_oid_buffer)

                crl_search_ref_pointer = new(Security, 'SecPolicySearchRef *')
                result = Security.SecPolicySearchCreate(
                    SecurityConst.CSSM_CERT_X_509v3,
                    crl_oid_pointer,
                    null(),
                    crl_search_ref_pointer
                )
                handle_sec_error(result)
                crl_search_ref = unwrap(crl_search_ref_pointer)

                crl_policy_ref_pointer = new(Security, 'SecPolicyRef *')
                result = Security.SecPolicySearchCopyNext(crl_search_ref, crl_policy_ref_pointer)
                handle_sec_error(result)
                crl_policy_ref = unwrap(crl_policy_ref_pointer)

                crl_struct_pointer = struct(Security, 'CSSM_APPLE_TP_CRL_OPTIONS')
                crl_struct = unwrap(crl_struct_pointer)
                crl_struct.Version = SecurityConst.CSSM_APPLE_TP_CRL_OPTS_VERSION
                crl_struct.CrlFlags = 0
                crl_struct_bytes = struct_bytes(crl_struct_pointer)

                cssm_data_pointer = struct(Security, 'CSSM_DATA')
                cssm_data = unwrap(cssm_data_pointer)
                cssm_data.Length = len(crl_struct_bytes)
                crl_struct_buffer = buffer_from_bytes(crl_struct_bytes)
                cssm_data.Data = cast(Security, 'char *', crl_struct_buffer)

                result = Security.SecPolicySetValue(crl_policy_ref, cssm_data_pointer)
                handle_sec_error(result)

                policy_array_ref = CFHelpers.cf_array_from_list([
                    ssl_policy_ref,
                    crl_policy_ref,
                    ocsp_policy_ref
                ])

                result = Security.SecTrustSetPolicies(trust_ref, policy_array_ref)
                handle_sec_error(result)

                if self._session._extra_trust_roots:
                    ca_cert_refs = []
                    ca_certs = []
                    for cert in self._session._extra_trust_roots:
                        ca_cert = load_certificate(cert)
                        ca_certs.append(ca_cert)
                        ca_cert_refs.append(ca_cert.sec_certificate_ref)

                    result = Security.SecTrustSetAnchorCertificatesOnly(trust_ref, False)
                    handle_sec_error(result)

                    array_ref = CFHelpers.cf_array_from_list(ca_cert_refs)
                    result = Security.SecTrustSetAnchorCertificates(trust_ref, array_ref)
                    handle_sec_error(result)

                result_pointer = new(Security, 'SecTrustResultType *')
                result = Security.SecTrustEvaluate(trust_ref, result_pointer)
                handle_sec_error(result)

                trust_result_code = deref(result_pointer)
                invalid_chain_error_codes = set([
                    SecurityConst.kSecTrustResultProceed,
                    SecurityConst.kSecTrustResultUnspecified
                ])
                if trust_result_code not in invalid_chain_error_codes:
                    handshake_result = SecurityConst.errSSLXCertChainInvalid
                else:
                    handshake_result = Security.SSLHandshake(session_context)
                    while handshake_result == SecurityConst.errSSLWouldBlock:
                        handshake_result = Security.SSLHandshake(session_context)

            self._done_handshake = True

            handshake_error_codes = set([
                SecurityConst.errSSLXCertChainInvalid,
                SecurityConst.errSSLCertExpired,
                SecurityConst.errSSLCertNotYetValid,
                SecurityConst.errSSLUnknownRootCert,
                SecurityConst.errSSLNoRootCert,
                SecurityConst.errSSLHostNameMismatch,
                SecurityConst.errSSLInternal,
            ])

            # In testing, only errSSLXCertChainInvalid was ever returned for
            # all of these different situations, however we include the others
            # for completeness. To get the real reason we have to use the
            # certificate from the handshake and use the deprecated function
            # SecTrustGetCssmResultCode().
            if handshake_result in handshake_error_codes:
                if trust_ref:
                    CoreFoundation.CFRelease(trust_ref)
                    trust_ref = None

                trust_ref_pointer = new(Security, 'SecTrustRef *')
                result = Security.SSLCopyPeerTrust(
                    session_context,
                    trust_ref_pointer
                )
                handle_sec_error(result)
                trust_ref = unwrap(trust_ref_pointer)

                result_code_pointer = new(Security, 'OSStatus *')
                result = Security.SecTrustGetCssmResultCode(trust_ref, result_code_pointer)
                result_code = deref(result_code_pointer)

                chain = extract_chain(self._server_hello)

                self_signed = False
                revoked = False
                expired = False
                not_yet_valid = False
                no_issuer = False
                cert = None
                bad_hostname = False

                if chain:
                    cert = chain[0]
                    oscrypto_cert = load_certificate(cert)
                    self_signed = oscrypto_cert.self_signed
                    revoked = result_code == SecurityConst.CSSMERR_TP_CERT_REVOKED
                    no_issuer = not self_signed and result_code == SecurityConst.CSSMERR_TP_NOT_TRUSTED
                    expired = result_code == SecurityConst.CSSMERR_TP_CERT_EXPIRED
                    not_yet_valid = result_code == SecurityConst.CSSMERR_TP_CERT_NOT_VALID_YET
                    bad_hostname = result_code == SecurityConst.CSSMERR_APPLETP_HOSTNAME_MISMATCH
                    validity_too_long = result_code == SecurityConst.CSSMERR_TP_CERT_SUSPENDED

                    # On macOS 10.12, some expired certificates return errSSLInternal
                    if osx_version_info >= (10, 12):
                        validity = cert['tbs_certificate']['validity']
                        not_before = validity['not_before'].chosen.native
                        not_after = validity['not_after'].chosen.native
                        utcnow = datetime.datetime.now(timezone.utc)
                        expired = not_after < utcnow
                        not_yet_valid = not_before > utcnow

                if chain and chain[0].hash_algo in set(['md5', 'md2']):
                    raise_weak_signature(chain[0])

                if revoked:
                    raise_revoked(cert)

                if bad_hostname:
                    raise_hostname(cert, self._hostname)

                elif expired or not_yet_valid:
                    raise_expired_not_yet_valid(cert)

                elif no_issuer:
                    raise_no_issuer(cert)

                elif self_signed:
                    raise_self_signed(cert)

                elif validity_too_long:
                    raise_lifetime_too_long(cert)

                if detect_client_auth_request(self._server_hello):
                    raise_client_auth()

                raise_verification(cert)

            if handshake_result == SecurityConst.errSSLPeerHandshakeFail:
                if detect_client_auth_request(self._server_hello):
                    raise_client_auth()
                raise_handshake()

            if handshake_result == SecurityConst.errSSLWeakPeerEphemeralDHKey:
                raise_dh_params()

            if handshake_result == SecurityConst.errSSLPeerProtocolVersion:
                raise_protocol_version()

            if handshake_result in set([SecurityConst.errSSLRecordOverflow, SecurityConst.errSSLProtocol]):
                self._server_hello += _read_remaining(self._socket)
                raise_protocol_error(self._server_hello)

            if handshake_result in set([SecurityConst.errSSLClosedNoNotify, SecurityConst.errSSLClosedAbort]):
                if not self._done_handshake:
                    self._server_hello += _read_remaining(self._socket)
                if detect_other_protocol(self._server_hello):
                    raise_protocol_error(self._server_hello)
                raise_disconnection()

            if osx_version_info < (10, 10):
                dh_params_length = get_dh_params_length(self._server_hello)
                if dh_params_length is not None and dh_params_length < 1024:
                    raise_dh_params()

            would_block = handshake_result == SecurityConst.errSSLWouldBlock
            server_auth_complete = handshake_result == SecurityConst.errSSLServerAuthCompleted
            manual_validation = self._session._manual_validation and server_auth_complete
            if not would_block and not manual_validation:
                handle_sec_error(handshake_result, TLSError)

            self._session_context = session_context

            protocol_const_pointer = new(Security, 'SSLProtocol *')
            result = Security.SSLGetNegotiatedProtocolVersion(
                session_context,
                protocol_const_pointer
            )
            handle_sec_error(result)
            protocol_const = deref(protocol_const_pointer)

            self._protocol = _PROTOCOL_CONST_STRING_MAP[protocol_const]

            cipher_int_pointer = new(Security, 'SSLCipherSuite *')
            result = Security.SSLGetNegotiatedCipher(
                session_context,
                cipher_int_pointer
            )
            handle_sec_error(result)
            cipher_int = deref(cipher_int_pointer)

            cipher_bytes = int_to_bytes(cipher_int, width=2)
            self._cipher_suite = CIPHER_SUITE_MAP.get(cipher_bytes, cipher_bytes)

            session_info = parse_session_info(
                self._server_hello,
                self._client_hello
            )
            self._compression = session_info['compression']
            self._session_id = session_info['session_id']
            self._session_ticket = session_info['session_ticket']

        except (OSError, socket_.error):
            if session_context:
                if osx_version_info < (10, 8):
                    result = Security.SSLDisposeContext(session_context)
                    handle_sec_error(result)
                else:
                    result = CoreFoundation.CFRelease(session_context)
                    handle_cf_error(result)

            self._session_context = None
            self.close()

            raise

        finally:
            # Trying to release crl_search_ref or ocsp_search_ref results in
            # a segmentation fault, so we do not do that

            if ssl_policy_ref:
                result = CoreFoundation.CFRelease(ssl_policy_ref)
                handle_cf_error(result)
                ssl_policy_ref = None

            if crl_policy_ref:
                result = CoreFoundation.CFRelease(crl_policy_ref)
                handle_cf_error(result)
                crl_policy_ref = None

            if ocsp_policy_ref:
                result = CoreFoundation.CFRelease(ocsp_policy_ref)
                handle_cf_error(result)
                ocsp_policy_ref = None

            if policy_array_ref:
                result = CoreFoundation.CFRelease(policy_array_ref)
                handle_cf_error(result)
                policy_array_ref = None

            if trust_ref:
                CoreFoundation.CFRelease(trust_ref)
                trust_ref = None

    def read(self, max_length):
        """
        Reads data from the TLS-wrapped socket

        :param max_length:
            The number of bytes to read - output may be less than this

        :raises:
            socket.socket - when a non-TLS socket error occurs
            oscrypto.errors.TLSError - when a TLS-related error occurs
            oscrypto.errors.TLSDisconnectError - when the connection disconnects
            oscrypto.errors.TLSGracefulDisconnectError - when the remote end gracefully closed the connection
            ValueError - when any of the parameters contain an invalid value
            TypeError - when any of the parameters are of the wrong type
            OSError - when an error is returned by the OS crypto library

        :return:
            A byte string of the data read
        """

        if not isinstance(max_length, int_types):
            raise TypeError(pretty_message(
                '''
                max_length must be an integer, not %s
                ''',
                type_name(max_length)
            ))

        if self._session_context is None:
            # Even if the session is closed, we can use
            # buffered data to respond to read requests
            if self._decrypted_bytes != b'':
                output = self._decrypted_bytes
                self._decrypted_bytes = b''
                return output

            self._raise_closed()

        buffered_length = len(self._decrypted_bytes)

        # If we already have enough buffered data, just use that
        if buffered_length >= max_length:
            output = self._decrypted_bytes[0:max_length]
            self._decrypted_bytes = self._decrypted_bytes[max_length:]
            return output

        # Don't block if we have buffered data available, since it is ok to
        # return less than the max_length
        if buffered_length > 0 and not self.select_read(0):
            output = self._decrypted_bytes
            self._decrypted_bytes = b''
            return output

        # Only read enough to get the requested amount when
        # combined with buffered data
        to_read = max_length - len(self._decrypted_bytes)

        read_buffer = buffer_from_bytes(to_read)
        processed_pointer = new(Security, 'size_t *')
        result = Security.SSLRead(
            self._session_context,
            read_buffer,
            to_read,
            processed_pointer
        )
        if self._exception is not None:
            exception = self._exception
            self._exception = None
            raise exception
        if result and result not in set([SecurityConst.errSSLWouldBlock, SecurityConst.errSSLClosedGraceful]):
            handle_sec_error(result, TLSError)

        if result and result == SecurityConst.errSSLClosedGraceful:
            self._gracefully_closed = True
            self._shutdown(False)
            self._raise_closed()

        bytes_read = deref(processed_pointer)
        output = self._decrypted_bytes + bytes_from_buffer(read_buffer, bytes_read)

        self._decrypted_bytes = output[max_length:]
        return output[0:max_length]

    def select_read(self, timeout=None):
        """
        Blocks until the socket is ready to be read from, or the timeout is hit

        :param timeout:
            A float - the period of time to wait for data to be read. None for
            no time limit.

        :return:
            A boolean - if data is ready to be read. Will only be False if
            timeout is not None.
        """

        # If we have buffered data, we consider a read possible
        if len(self._decrypted_bytes) > 0:
            return True

        read_ready, _, _ = select.select([self._socket], [], [], timeout)
        return len(read_ready) > 0

    def read_until(self, marker):
        """
        Reads data from the socket until a marker is found. Data read includes
        the marker.

        :param marker:
            A byte string or regex object from re.compile(). Used to determine
            when to stop reading. Regex objects are more inefficient since
            they must scan the entire byte string of read data each time data
            is read off the socket.

        :return:
            A byte string of the data read, including the marker
        """

        if not isinstance(marker, byte_cls) and not isinstance(marker, Pattern):
            raise TypeError(pretty_message(
                '''
                marker must be a byte string or compiled regex object, not %s
                ''',
                type_name(marker)
            ))

        output = b''

        is_regex = isinstance(marker, Pattern)

        while True:
            if len(self._decrypted_bytes) > 0:
                chunk = self._decrypted_bytes
                self._decrypted_bytes = b''
            else:
                to_read = self._os_buffered_size() or 8192
                chunk = self.read(to_read)

            offset = len(output)
            output += chunk

            if is_regex:
                match = marker.search(output)
                if match is not None:
                    end = match.end()
                    break
            else:
                # If the marker was not found last time, we have to start
                # at a position where the marker would have its final char
                # in the newly read chunk
                start = max(0, offset - len(marker) - 1)
                match = output.find(marker, start)
                if match != -1:
                    end = match + len(marker)
                    break

        self._decrypted_bytes = output[end:] + self._decrypted_bytes
        return output[0:end]

    def _os_buffered_size(self):
        """
        Returns the number of bytes of decrypted data stored in the Secure
        Transport read buffer. This amount of data can be read from SSLRead()
        without calling self._socket.recv().

        :return:
            An integer - the number of available bytes
        """

        num_bytes_pointer = new(Security, 'size_t *')
        result = Security.SSLGetBufferedReadSize(
            self._session_context,
            num_bytes_pointer
        )
        handle_sec_error(result)

        return deref(num_bytes_pointer)

    def read_line(self):
        r"""
        Reads a line from the socket, including the line ending of "\r\n", "\r",
        or "\n"

        :return:
            A byte string of the next line from the socket
        """

        return self.read_until(_line_regex)

    def read_exactly(self, num_bytes):
        """
        Reads exactly the specified number of bytes from the socket

        :param num_bytes:
            An integer - the exact number of bytes to read

        :return:
            A byte string of the data that was read
        """

        output = b''
        remaining = num_bytes
        while remaining > 0:
            output += self.read(remaining)
            remaining = num_bytes - len(output)

        return output

    def write(self, data):
        """
        Writes data to the TLS-wrapped socket

        :param data:
            A byte string to write to the socket

        :raises:
            socket.socket - when a non-TLS socket error occurs
            oscrypto.errors.TLSError - when a TLS-related error occurs
            oscrypto.errors.TLSDisconnectError - when the connection disconnects
            oscrypto.errors.TLSGracefulDisconnectError - when the remote end gracefully closed the connection
            ValueError - when any of the parameters contain an invalid value
            TypeError - when any of the parameters are of the wrong type
            OSError - when an error is returned by the OS crypto library
        """

        if self._session_context is None:
            self._raise_closed()

        processed_pointer = new(Security, 'size_t *')

        data_len = len(data)
        while data_len:
            write_buffer = buffer_from_bytes(data)
            result = Security.SSLWrite(
                self._session_context,
                write_buffer,
                data_len,
                processed_pointer
            )
            if self._exception is not None:
                exception = self._exception
                self._exception = None
                raise exception
            handle_sec_error(result, TLSError)

            bytes_written = deref(processed_pointer)
            data = data[bytes_written:]
            data_len = len(data)
            if data_len > 0:
                self.select_write()

    def select_write(self, timeout=None):
        """
        Blocks until the socket is ready to be written to, or the timeout is hit

        :param timeout:
            A float - the period of time to wait for the socket to be ready to
            written to. None for no time limit.

        :return:
            A boolean - if the socket is ready for writing. Will only be False
            if timeout is not None.
        """

        _, write_ready, _ = select.select([], [self._socket], [], timeout)
        return len(write_ready) > 0

    def _shutdown(self, manual):
        """
        Shuts down the TLS session and then shuts down the underlying socket

        :param manual:
            A boolean if the connection was manually shutdown
        """

        if self._session_context is None:
            return

        # Ignore error during close in case other end closed already
        result = Security.SSLClose(self._session_context)

        if osx_version_info < (10, 8):
            result = Security.SSLDisposeContext(self._session_context)
            handle_sec_error(result)
        else:
            result = CoreFoundation.CFRelease(self._session_context)
            handle_cf_error(result)

        self._session_context = None

        if manual:
            self._local_closed = True

        try:
            self._socket.shutdown(socket_.SHUT_RDWR)
        except (socket_.error):
            pass

    def shutdown(self):
        """
        Shuts down the TLS session and then shuts down the underlying socket
        """

        self._shutdown(True)

    def close(self):
        """
        Shuts down the TLS session and socket and forcibly closes it
        """

        try:
            self.shutdown()

        finally:
            if self._socket:
                try:
                    self._socket.close()
                except (socket_.error):
                    pass
                self._socket = None

            if self._connection_id in _socket_refs:
                del _socket_refs[self._connection_id]

    def _read_certificates(self):
        """
        Reads end-entity and intermediate certificate information from the
        TLS session
        """

        trust_ref = None
        cf_data_ref = None
        result = None

        try:
            trust_ref_pointer = new(Security, 'SecTrustRef *')
            result = Security.SSLCopyPeerTrust(
                self._session_context,
                trust_ref_pointer
            )
            handle_sec_error(result)

            trust_ref = unwrap(trust_ref_pointer)

            number_certs = Security.SecTrustGetCertificateCount(trust_ref)

            self._intermediates = []

            for index in range(0, number_certs):
                sec_certificate_ref = Security.SecTrustGetCertificateAtIndex(
                    trust_ref,
                    index
                )
                cf_data_ref = Security.SecCertificateCopyData(sec_certificate_ref)

                cert_data = CFHelpers.cf_data_to_bytes(cf_data_ref)

                result = CoreFoundation.CFRelease(cf_data_ref)
                handle_cf_error(result)
                cf_data_ref = None

                cert = Asn1Certificate.load(cert_data)

                if index == 0:
                    self._certificate = cert
                else:
                    self._intermediates.append(cert)

        finally:
            if trust_ref:
                result = CoreFoundation.CFRelease(trust_ref)
                handle_cf_error(result)
            if cf_data_ref:
                result = CoreFoundation.CFRelease(cf_data_ref)
                handle_cf_error(result)

    def _raise_closed(self):
        """
        Raises an exception describing if the local or remote end closed the
        connection
        """

        if self._local_closed:
            raise TLSDisconnectError('The connection was already closed')
        elif self._gracefully_closed:
            raise TLSGracefulDisconnectError('The remote end closed the connection')
        else:
            raise TLSDisconnectError('The connection was closed')

    @property
    def certificate(self):
        """
        An asn1crypto.x509.Certificate object of the end-entity certificate
        presented by the server
        """

        if self._session_context is None:
            self._raise_closed()

        if self._certificate is None:
            self._read_certificates()

        return self._certificate

    @property
    def intermediates(self):
        """
        A list of asn1crypto.x509.Certificate objects that were presented as
        intermediates by the server
        """

        if self._session_context is None:
            self._raise_closed()

        if self._certificate is None:
            self._read_certificates()

        return self._intermediates

    @property
    def cipher_suite(self):
        """
        A unicode string of the IANA cipher suite name of the negotiated
        cipher suite
        """

        return self._cipher_suite

    @property
    def protocol(self):
        """
        A unicode string of: "TLSv1.2", "TLSv1.1", "TLSv1", "SSLv3"
        """

        return self._protocol

    @property
    def compression(self):
        """
        A boolean if compression is enabled
        """

        return self._compression

    @property
    def session_id(self):
        """
        A unicode string of "new" or "reused" or None for no ticket
        """

        return self._session_id

    @property
    def session_ticket(self):
        """
        A unicode string of "new" or "reused" or None for no ticket
        """

        return self._session_ticket

    @property
    def session(self):
        """
        The oscrypto.tls.TLSSession object used for this connection
        """

        return self._session

    @property
    def hostname(self):
        """
        A unicode string of the TLS server domain name or IP address
        """

        return self._hostname

    @property
    def port(self):
        """
        An integer of the port number the socket is connected to
        """

        return self.socket.getpeername()[1]

    @property
    def socket(self):
        """
        The underlying socket.socket connection
        """

        if self._session_context is None:
            self._raise_closed()

        return self._socket

    def __del__(self):
        self.close()
