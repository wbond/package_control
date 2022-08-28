# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import sys
import re
import socket as socket_
import select
import numbers

from ._libssl import libssl, LibsslConst
from ._libcrypto import libcrypto, libcrypto_version_info, handle_openssl_error, peek_openssl_error
from .. import _backend_config
from .._asn1 import Certificate as Asn1Certificate
from .._errors import pretty_message
from .._ffi import null, bytes_from_buffer, buffer_from_bytes, is_null, buffer_pointer
from .._types import type_name, str_cls, byte_cls, int_types
from ..errors import TLSError, TLSDisconnectError, TLSGracefulDisconnectError
from .._tls import (
    detect_client_auth_request,
    extract_chain,
    get_dh_params_length,
    parse_session_info,
    raise_client_auth,
    raise_dh_params,
    raise_disconnection,
    raise_expired_not_yet_valid,
    raise_handshake,
    raise_hostname,
    raise_no_issuer,
    raise_protocol_error,
    raise_protocol_version,
    raise_self_signed,
    raise_verification,
    raise_weak_signature,
    parse_tls_records,
    parse_handshake_messages,
)
from .asymmetric import load_certificate, Certificate
from ..keys import parse_certificate
from ..trust_list import get_path

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


_trust_list_path = _backend_config().get('trust_list_path')
_line_regex = re.compile(b'(\r\n|\r|\n)')
_PROTOCOL_MAP = {
    'SSLv2': LibsslConst.SSL_OP_NO_SSLv2,
    'SSLv3': LibsslConst.SSL_OP_NO_SSLv3,
    'TLSv1': LibsslConst.SSL_OP_NO_TLSv1,
    'TLSv1.1': LibsslConst.SSL_OP_NO_TLSv1_1,
    'TLSv1.2': LibsslConst.SSL_OP_NO_TLSv1_2,
}


def _homogenize_openssl3_error(error_tuple):
    """
    Takes a 3-element tuple from peek_openssl_error() and modifies it
    to handle the changes in OpenSSL 3.0. That release removed the
    concept of an error function, meaning the second item in the tuple
    will always be 0.

    :param error_tuple:
        A 3-element tuple of integers

    :return:
        A 3-element tuple of integers
    """

    if libcrypto_version_info < (3,):
        return error_tuple
    return (error_tuple[0], 0, error_tuple[2])


class TLSSession(object):
    """
    A TLS session object that multiple TLSSocket objects can share for the
    sake of session reuse
    """

    _protocols = None
    _ciphers = None
    _manual_validation = None
    _extra_trust_roots = None
    _ssl_ctx = None
    _ssl_session = None

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

        valid_protocols = set(['SSLv3', 'TLSv1', 'TLSv1.1', 'TLSv1.2'])
        unsupported_protocols = protocol - valid_protocols
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

        ssl_ctx = None
        try:
            if libcrypto_version_info < (1, 1):
                method = libssl.SSLv23_method()
            else:
                method = libssl.TLS_method()
            ssl_ctx = libssl.SSL_CTX_new(method)
            if is_null(ssl_ctx):
                handle_openssl_error(0)
            self._ssl_ctx = ssl_ctx

            libssl.SSL_CTX_set_timeout(ssl_ctx, 600)

            # Allow caching SSL sessions
            libssl.SSL_CTX_ctrl(
                ssl_ctx,
                LibsslConst.SSL_CTRL_SET_SESS_CACHE_MODE,
                LibsslConst.SSL_SESS_CACHE_CLIENT,
                null()
            )

            if sys.platform in set(['win32', 'darwin']):
                trust_list_path = _trust_list_path
                if trust_list_path is None:
                    trust_list_path = get_path()

                if sys.platform == 'win32':
                    path_encoding = 'mbcs'
                else:
                    path_encoding = 'utf-8'
                result = libssl.SSL_CTX_load_verify_locations(
                    ssl_ctx,
                    trust_list_path.encode(path_encoding),
                    null()
                )

            else:
                result = libssl.SSL_CTX_set_default_verify_paths(ssl_ctx)
            handle_openssl_error(result)

            verify_mode = LibsslConst.SSL_VERIFY_NONE if manual_validation else LibsslConst.SSL_VERIFY_PEER
            libssl.SSL_CTX_set_verify(ssl_ctx, verify_mode, null())

            # Modern cipher suite list from https://wiki.mozilla.org/Security/Server_Side_TLS late August 2015
            result = libssl.SSL_CTX_set_cipher_list(
                ssl_ctx,
                (
                    b'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:'
                    b'ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:'
                    b'DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:'
                    b'kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:'
                    b'ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:'
                    b'ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:'
                    b'DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:'
                    b'DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:'
                    b'AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:'
                    b'AES128-SHA:AES256-SHA:AES:CAMELLIA:DES-CBC3-SHA:!aNULL:!eNULL:'
                    b'!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:!EDH-DSS-DES-CBC3-SHA:'
                    b'!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA'
                )
            )
            handle_openssl_error(result)

            disabled_protocols = set(['SSLv2'])
            disabled_protocols |= (valid_protocols - self._protocols)
            for disabled_protocol in disabled_protocols:
                libssl.SSL_CTX_ctrl(
                    ssl_ctx,
                    LibsslConst.SSL_CTRL_OPTIONS,
                    _PROTOCOL_MAP[disabled_protocol],
                    null()
                )

            if self._extra_trust_roots:
                x509_store = libssl.SSL_CTX_get_cert_store(ssl_ctx)
                for cert in self._extra_trust_roots:
                    oscrypto_cert = load_certificate(cert)
                    result = libssl.X509_STORE_add_cert(
                        x509_store,
                        oscrypto_cert.x509
                    )
                    handle_openssl_error(result)

        except (Exception):
            if ssl_ctx:
                libssl.SSL_CTX_free(ssl_ctx)
            self._ssl_ctx = None
            raise

    def __del__(self):
        if self._ssl_ctx:
            libssl.SSL_CTX_free(self._ssl_ctx)
            self._ssl_ctx = None

        if self._ssl_session:
            libssl.SSL_SESSION_free(self._ssl_session)
            self._ssl_session = None


class TLSSocket(object):
    """
    A wrapper around a socket.socket that adds TLS
    """

    _socket = None

    # An oscrypto.tls.TLSSession object
    _session = None

    # An OpenSSL SSL struct pointer
    _ssl = None

    # OpenSSL memory bios used for reading/writing data to and
    # from the socket
    _rbio = None
    _wbio = None

    # Size of _bio_write_buffer and _read_buffer
    _buffer_size = 8192

    # A buffer used to pull bytes out of the _wbio memory bio to
    # be written to the socket
    _bio_write_buffer = None

    # A buffer used to push bytes into the _rbio memory bio to
    # be decrypted by OpenSSL
    _read_buffer = None

    # Raw ciphertext from the socker that hasn't need fed to OpenSSL yet
    _raw_bytes = None

    # Plaintext that has been decrypted, but not asked for yet
    _decrypted_bytes = None

    _hostname = None

    _certificate = None
    _intermediates = None

    _protocol = None
    _cipher_suite = None
    _compression = None
    _session_id = None
    _session_ticket = None

    # If we explicitly asked for the connection to be closed
    _local_closed = False

    _gracefully_closed = False

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

        self._raw_bytes = b''
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

        self._ssl = None
        self._rbio = None
        self._wbio = None

        try:
            self._ssl = libssl.SSL_new(self._session._ssl_ctx)
            if is_null(self._ssl):
                self._ssl = None
                handle_openssl_error(0)

            mem_bio = libssl.BIO_s_mem()

            self._rbio = libssl.BIO_new(mem_bio)
            if is_null(self._rbio):
                handle_openssl_error(0)

            self._wbio = libssl.BIO_new(mem_bio)
            if is_null(self._wbio):
                handle_openssl_error(0)

            libssl.SSL_set_bio(self._ssl, self._rbio, self._wbio)

            utf8_domain = self._hostname.encode('utf-8')
            libssl.SSL_ctrl(
                self._ssl,
                LibsslConst.SSL_CTRL_SET_TLSEXT_HOSTNAME,
                LibsslConst.TLSEXT_NAMETYPE_host_name,
                utf8_domain
            )

            libssl.SSL_set_connect_state(self._ssl)

            if self._session._ssl_session:
                libssl.SSL_set_session(self._ssl, self._session._ssl_session)

            self._bio_write_buffer = buffer_from_bytes(self._buffer_size)
            self._read_buffer = buffer_from_bytes(self._buffer_size)

            handshake_server_bytes = b''
            handshake_client_bytes = b''

            while True:
                result = libssl.SSL_do_handshake(self._ssl)
                handshake_client_bytes += self._raw_write()

                if result == 1:
                    break

                error = libssl.SSL_get_error(self._ssl, result)
                if error == LibsslConst.SSL_ERROR_WANT_READ:
                    chunk = self._raw_read()
                    if chunk == b'':
                        if handshake_server_bytes == b'':
                            raise_disconnection()
                        if detect_client_auth_request(handshake_server_bytes):
                            raise_client_auth()
                        raise_protocol_error(handshake_server_bytes)
                    handshake_server_bytes += chunk

                elif error == LibsslConst.SSL_ERROR_WANT_WRITE:
                    handshake_client_bytes += self._raw_write()

                elif error == LibsslConst.SSL_ERROR_ZERO_RETURN:
                    self._gracefully_closed = True
                    self._shutdown(False)
                    self._raise_closed()

                else:
                    info = peek_openssl_error()

                    dh_key_info_1 = (
                        LibsslConst.ERR_LIB_SSL,
                        LibsslConst.SSL_F_SSL3_CHECK_CERT_AND_ALGORITHM,
                        LibsslConst.SSL_R_DH_KEY_TOO_SMALL
                    )
                    dh_key_info_1 = _homogenize_openssl3_error(dh_key_info_1)

                    dh_key_info_2 = (
                        LibsslConst.ERR_LIB_SSL,
                        LibsslConst.SSL_F_TLS_PROCESS_SKE_DHE,
                        LibsslConst.SSL_R_DH_KEY_TOO_SMALL
                    )
                    dh_key_info_2 = _homogenize_openssl3_error(dh_key_info_2)

                    dh_key_info_3 = (
                        LibsslConst.ERR_LIB_SSL,
                        LibsslConst.SSL_F_SSL3_GET_KEY_EXCHANGE,
                        LibsslConst.SSL_R_BAD_DH_P_LENGTH
                    )
                    dh_key_info_3 = _homogenize_openssl3_error(dh_key_info_3)

                    if info == dh_key_info_1 or info == dh_key_info_2 or info == dh_key_info_3:
                        raise_dh_params()

                    if libcrypto_version_info < (1, 1):
                        unknown_protocol_info = (
                            LibsslConst.ERR_LIB_SSL,
                            LibsslConst.SSL_F_SSL23_GET_SERVER_HELLO,
                            LibsslConst.SSL_R_UNKNOWN_PROTOCOL
                        )
                    else:
                        unknown_protocol_info = (
                            LibsslConst.ERR_LIB_SSL,
                            LibsslConst.SSL_F_SSL3_GET_RECORD,
                            LibsslConst.SSL_R_WRONG_VERSION_NUMBER
                        )
                        unknown_protocol_info = _homogenize_openssl3_error(unknown_protocol_info)

                    if info == unknown_protocol_info:
                        raise_protocol_error(handshake_server_bytes)

                    tls_version_info_error = (
                        LibsslConst.ERR_LIB_SSL,
                        LibsslConst.SSL_F_SSL23_GET_SERVER_HELLO,
                        LibsslConst.SSL_R_TLSV1_ALERT_PROTOCOL_VERSION
                    )
                    tls_version_info_error = _homogenize_openssl3_error(tls_version_info_error)
                    if info == tls_version_info_error:
                        raise_protocol_version()

                    handshake_error_info = (
                        LibsslConst.ERR_LIB_SSL,
                        LibsslConst.SSL_F_SSL23_GET_SERVER_HELLO,
                        LibsslConst.SSL_R_SSLV3_ALERT_HANDSHAKE_FAILURE
                    )
                    # OpenSSL 3.0 no longer has func codes, so this can be confused
                    # with the following handler which needs to check for client auth
                    if libcrypto_version_info < (3, ) and info == handshake_error_info:
                        raise_handshake()

                    handshake_failure_info = (
                        LibsslConst.ERR_LIB_SSL,
                        LibsslConst.SSL_F_SSL3_READ_BYTES,
                        LibsslConst.SSL_R_SSLV3_ALERT_HANDSHAKE_FAILURE
                    )
                    handshake_failure_info = _homogenize_openssl3_error(handshake_failure_info)
                    if info == handshake_failure_info:
                        saw_client_auth = False
                        for record_type, _, record_data in parse_tls_records(handshake_server_bytes):
                            if record_type != b'\x16':
                                continue
                            for message_type, message_data in parse_handshake_messages(record_data):
                                if message_type == b'\x0d':
                                    saw_client_auth = True
                                    break
                        if saw_client_auth:
                            raise_client_auth()
                        raise_handshake()

                    if libcrypto_version_info < (1, 1):
                        cert_verify_failed_info = (
                            LibsslConst.ERR_LIB_SSL,
                            LibsslConst.SSL_F_SSL3_GET_SERVER_CERTIFICATE,
                            LibsslConst.SSL_R_CERTIFICATE_VERIFY_FAILED
                        )
                    else:
                        cert_verify_failed_info = (
                            LibsslConst.ERR_LIB_SSL,
                            LibsslConst.SSL_F_TLS_PROCESS_SERVER_CERTIFICATE,
                            LibsslConst.SSL_R_CERTIFICATE_VERIFY_FAILED
                        )
                        cert_verify_failed_info = _homogenize_openssl3_error(cert_verify_failed_info)

                    # It would appear that some versions of OpenSSL (such as on Fedora 30)
                    # don't even have the MD5 digest algorithm included any longer? To
                    # give a more useful error message we handle this specifically.
                    unknown_hash_algo_info = (
                        LibsslConst.ERR_LIB_ASN1,
                        LibsslConst.ASN1_F_ASN1_ITEM_VERIFY,
                        LibsslConst.ASN1_R_UNKNOWN_MESSAGE_DIGEST_ALGORITHM
                    )
                    unknown_hash_algo_info = _homogenize_openssl3_error(unknown_hash_algo_info)

                    if info == unknown_hash_algo_info:
                        chain = extract_chain(handshake_server_bytes)
                        if chain:
                            cert = chain[0]
                            oscrypto_cert = load_certificate(cert)
                            if oscrypto_cert.asn1.hash_algo in set(['md5', 'md2']):
                                raise_weak_signature(oscrypto_cert)

                    if info == cert_verify_failed_info:
                        verify_result = libssl.SSL_get_verify_result(self._ssl)
                        chain = extract_chain(handshake_server_bytes)

                        self_signed = False
                        time_invalid = False
                        no_issuer = False
                        cert = None
                        oscrypto_cert = None

                        if chain:
                            cert = chain[0]
                            oscrypto_cert = load_certificate(cert)
                            self_signed = oscrypto_cert.self_signed

                            issuer_error_codes = set([
                                LibsslConst.X509_V_ERR_DEPTH_ZERO_SELF_SIGNED_CERT,
                                LibsslConst.X509_V_ERR_SELF_SIGNED_CERT_IN_CHAIN,
                                LibsslConst.X509_V_ERR_UNABLE_TO_GET_ISSUER_CERT_LOCALLY
                            ])
                            if verify_result in issuer_error_codes:
                                no_issuer = not self_signed

                            time_error_codes = set([
                                LibsslConst.X509_V_ERR_CERT_HAS_EXPIRED,
                                LibsslConst.X509_V_ERR_CERT_NOT_YET_VALID
                            ])
                            time_invalid = verify_result in time_error_codes

                        if time_invalid:
                            raise_expired_not_yet_valid(cert)
                        if no_issuer:
                            raise_no_issuer(cert)
                        if self_signed:
                            raise_self_signed(cert)
                        if oscrypto_cert and oscrypto_cert.asn1.hash_algo in set(['md5', 'md2']):
                            raise_weak_signature(oscrypto_cert)
                        raise_verification(cert)

                    handle_openssl_error(0, TLSError)

            session_info = parse_session_info(
                handshake_server_bytes,
                handshake_client_bytes
            )
            self._protocol = session_info['protocol']
            self._cipher_suite = session_info['cipher_suite']
            self._compression = session_info['compression']
            self._session_id = session_info['session_id']
            self._session_ticket = session_info['session_ticket']

            if self._cipher_suite.find('_DHE_') != -1:
                dh_params_length = get_dh_params_length(handshake_server_bytes)
                if dh_params_length < 1024:
                    self.close()
                    raise_dh_params()

            # When saving the session for future requests, we use
            # SSL_get1_session() variant to increase the reference count. This
            # prevents the session from being freed when one connection closes
            # before another is opened. However, since we increase the ref
            # count, we also have to explicitly free any previous session.
            if self._session_id == 'new' or self._session_ticket == 'new':
                if self._session._ssl_session:
                    libssl.SSL_SESSION_free(self._session._ssl_session)
                self._session._ssl_session = libssl.SSL_get1_session(self._ssl)

            if not self._session._manual_validation:
                if self.certificate.hash_algo in set(['md5', 'md2']):
                    raise_weak_signature(self.certificate)

                # OpenSSL does not do hostname or IP address checking in the end
                # entity certificate, so we must perform that check
                if not self.certificate.is_valid_domain_ip(self._hostname):
                    raise_hostname(self.certificate, self._hostname)

        except (OSError, socket_.error):
            if self._ssl:
                libssl.SSL_free(self._ssl)
                self._ssl = None
                self._rbio = None
                self._wbio = None
            # The BIOs are freed by SSL_free(), so we only need to free
            # them if for some reason SSL_free() was not called
            else:
                if self._rbio:
                    libssl.BIO_free(self._rbio)
                    self._rbio = None
                if self._wbio:
                    libssl.BIO_free(self._wbio)
                    self._wbio = None
            self.close()

            raise

    def _raw_read(self):
        """
        Reads data from the socket and writes it to the memory bio
        used by libssl to decrypt the data. Returns the unencrypted
        data for the purpose of debugging handshakes.

        :return:
            A byte string of ciphertext from the socket. Used for
            debugging the handshake only.
        """

        data = self._raw_bytes
        try:
            data += self._socket.recv(8192)
        except (socket_.error):
            pass
        output = data
        written = libssl.BIO_write(self._rbio, data, len(data))
        self._raw_bytes = data[written:]
        return output

    def _raw_write(self):
        """
        Takes ciphertext from the memory bio and writes it to the
        socket.

        :return:
            A byte string of ciphertext going to the socket. Used
            for debugging the handshake only.
        """

        data_available = libssl.BIO_ctrl_pending(self._wbio)
        if data_available == 0:
            return b''
        to_read = min(self._buffer_size, data_available)
        read = libssl.BIO_read(self._wbio, self._bio_write_buffer, to_read)
        to_write = bytes_from_buffer(self._bio_write_buffer, read)
        output = to_write
        while len(to_write):
            raise_disconnect = False
            try:
                sent = self._socket.send(to_write)
            except (socket_.error) as e:
                # Handle ECONNRESET and EPIPE
                if e.errno == 104 or e.errno == 32:
                    raise_disconnect = True
                # Handle EPROTOTYPE. Newer versions of macOS will return this
                # if we try to call send() while the socket is being torn down
                elif sys.platform == 'darwin' and e.errno == 41:
                    raise_disconnect = True
                else:
                    raise

            if raise_disconnect:
                raise_disconnection()
            to_write = to_write[sent:]
            if len(to_write):
                self.select_write()
        return output

    def read(self, max_length):
        """
        Reads data from the TLS-wrapped socket

        :param max_length:
            The number of bytes to read - output may be less than this

        :raises:
            socket.socket - when a non-TLS socket error occurs
            oscrypto.errors.TLSError - when a TLS-related error occurs
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

        buffered_length = len(self._decrypted_bytes)

        # If we already have enough buffered data, just use that
        if buffered_length >= max_length:
            output = self._decrypted_bytes[0:max_length]
            self._decrypted_bytes = self._decrypted_bytes[max_length:]
            return output

        if self._ssl is None:
            self._raise_closed()

        # Don't block if we have buffered data available, since it is ok to
        # return less than the max_length
        if buffered_length > 0 and not self.select_read(0):
            output = self._decrypted_bytes
            self._decrypted_bytes = b''
            return output

        # Only read enough to get the requested amount when
        # combined with buffered data
        to_read = min(self._buffer_size, max_length - buffered_length)

        output = self._decrypted_bytes

        # The SSL_read() loop handles renegotiations, so we need to handle
        # requests for both reads and writes
        again = True
        while again:
            again = False
            result = libssl.SSL_read(self._ssl, self._read_buffer, to_read)
            self._raw_write()
            if result <= 0:

                error = libssl.SSL_get_error(self._ssl, result)
                if error == LibsslConst.SSL_ERROR_WANT_READ:
                    if self._raw_read() != b'':
                        again = True
                        continue
                    raise_disconnection()

                elif error == LibsslConst.SSL_ERROR_WANT_WRITE:
                    self._raw_write()
                    again = True
                    continue

                elif error == LibsslConst.SSL_ERROR_ZERO_RETURN:
                    self._gracefully_closed = True
                    self._shutdown(False)
                    break

                else:
                    handle_openssl_error(0, TLSError)

            output += bytes_from_buffer(self._read_buffer, result)

        if self._gracefully_closed and len(output) == 0:
            self._raise_closed()

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
                if self._ssl is None:
                    self._raise_closed()
                to_read = libssl.SSL_pending(self._ssl) or 8192
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
            ValueError - when any of the parameters contain an invalid value
            TypeError - when any of the parameters are of the wrong type
            OSError - when an error is returned by the OS crypto library
        """

        data_len = len(data)
        while data_len:
            if self._ssl is None:
                self._raise_closed()
            result = libssl.SSL_write(self._ssl, data, data_len)
            self._raw_write()
            if result <= 0:

                error = libssl.SSL_get_error(self._ssl, result)
                if error == LibsslConst.SSL_ERROR_WANT_READ:
                    if self._raw_read() != b'':
                        continue
                    raise_disconnection()

                elif error == LibsslConst.SSL_ERROR_WANT_WRITE:
                    self._raw_write()
                    continue

                elif error == LibsslConst.SSL_ERROR_ZERO_RETURN:
                    self._gracefully_closed = True
                    self._shutdown(False)
                    self._raise_closed()

                else:
                    handle_openssl_error(0, TLSError)

            data = data[result:]
            data_len = len(data)

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

        if self._ssl is None:
            return

        while True:
            result = libssl.SSL_shutdown(self._ssl)

            # Don't be noisy if the socket is already closed
            try:
                self._raw_write()
            except (TLSDisconnectError):
                pass

            if result >= 0:
                break
            if result < 0:
                error = libssl.SSL_get_error(self._ssl, result)
                if error == LibsslConst.SSL_ERROR_WANT_READ:
                    if self._raw_read() != b'':
                        continue
                    else:
                        break

                elif error == LibsslConst.SSL_ERROR_WANT_WRITE:
                    self._raw_write()
                    continue

                else:
                    handle_openssl_error(0, TLSError)

        if manual:
            self._local_closed = True

        libssl.SSL_free(self._ssl)
        self._ssl = None
        # BIOs are freed by SSL_free()
        self._rbio = None
        self._wbio = None

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

    def _read_certificates(self):
        """
        Reads end-entity and intermediate certificate information from the
        TLS session
        """

        stack_pointer = libssl.SSL_get_peer_cert_chain(self._ssl)
        if is_null(stack_pointer):
            handle_openssl_error(0, TLSError)

        if libcrypto_version_info < (1, 1):
            number_certs = libssl.sk_num(stack_pointer)
        else:
            number_certs = libssl.OPENSSL_sk_num(stack_pointer)

        self._intermediates = []

        for index in range(0, number_certs):
            if libcrypto_version_info < (1, 1):
                x509_ = libssl.sk_value(stack_pointer, index)
            else:
                x509_ = libssl.OPENSSL_sk_value(stack_pointer, index)
            buffer_size = libcrypto.i2d_X509(x509_, null())
            cert_buffer = buffer_from_bytes(buffer_size)
            cert_pointer = buffer_pointer(cert_buffer)
            cert_length = libcrypto.i2d_X509(x509_, cert_pointer)
            handle_openssl_error(cert_length)
            cert_data = bytes_from_buffer(cert_buffer, cert_length)

            cert = Asn1Certificate.load(cert_data)

            if index == 0:
                self._certificate = cert
            else:
                self._intermediates.append(cert)

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

        if self._ssl is None:
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

        if self._ssl is None:
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

        if self._ssl is None:
            self._raise_closed()

        return self._socket

    def __del__(self):
        self.close()
