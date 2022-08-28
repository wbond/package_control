# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import sys
import re
import socket as socket_
import select
import numbers

from .._asn1 import Certificate as Asn1Certificate
from .._errors import pretty_message
from .._ffi import (
    buffer_from_bytes,
    buffer_from_unicode,
    bytes_from_buffer,
    cast,
    deref,
    is_null,
    native,
    new,
    null,
    ref,
    sizeof,
    struct,
    unwrap,
    write_to_buffer,
)
from ._secur32 import secur32, Secur32Const, handle_error
from ._crypt32 import crypt32, Crypt32Const, handle_error as handle_crypt32_error
from ._kernel32 import kernel32
from .._types import type_name, str_cls, byte_cls, int_types
from ..errors import TLSError, TLSVerificationError, TLSDisconnectError, TLSGracefulDisconnectError
from .._tls import (
    detect_client_auth_request,
    detect_other_protocol,
    extract_chain,
    get_dh_params_length,
    parse_alert,
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
    raise_revoked,
    raise_self_signed,
    raise_verification,
    raise_weak_signature,
)
from .asymmetric import load_certificate, Certificate
from ..keys import parse_certificate

if sys.version_info < (3,):
    range = xrange  # noqa
    socket_error_cls = socket_.error
else:
    socket_error_cls = WindowsError

if sys.version_info < (3, 7):
    Pattern = re._pattern_type
else:
    Pattern = re.Pattern


__all__ = [
    'TLSSession',
    'TLSSocket',
]


_line_regex = re.compile(b'(\r\n|\r|\n)')

_gwv = sys.getwindowsversion()
_win_version_info = (_gwv[0], _gwv[1])


class _TLSDowngradeError(TLSVerificationError):

    pass


class _TLSRetryError(TLSError):

    """
    TLSv1.2 on Windows 7 and 8 seems to have isuses with some DHE_RSA
    ServerKeyExchange messages due to variable length integer encoding. This
    exception is used to trigger a reconnection to attempt the handshake again.
    """

    pass


class TLSSession(object):
    """
    A TLS session object that multiple TLSSocket objects can share for the
    sake of session reuse
    """

    _protocols = None
    _ciphers = None
    _manual_validation = None
    _extra_trust_roots = None
    _credentials_handle = None

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

        self._obtain_credentials()

    def _obtain_credentials(self):
        """
        Obtains a credentials handle from secur32.dll for use with SChannel
        """

        protocol_values = {
            'SSLv3': Secur32Const.SP_PROT_SSL3_CLIENT,
            'TLSv1': Secur32Const.SP_PROT_TLS1_CLIENT,
            'TLSv1.1': Secur32Const.SP_PROT_TLS1_1_CLIENT,
            'TLSv1.2': Secur32Const.SP_PROT_TLS1_2_CLIENT,
        }
        protocol_bit_mask = 0
        for key, value in protocol_values.items():
            if key in self._protocols:
                protocol_bit_mask |= value

        algs = [
            Secur32Const.CALG_AES_128,
            Secur32Const.CALG_AES_256,
            Secur32Const.CALG_3DES,
            Secur32Const.CALG_SHA1,
            Secur32Const.CALG_ECDHE,
            Secur32Const.CALG_DH_EPHEM,
            Secur32Const.CALG_RSA_KEYX,
            Secur32Const.CALG_RSA_SIGN,
            Secur32Const.CALG_ECDSA,
            Secur32Const.CALG_DSS_SIGN,
        ]
        if 'TLSv1.2' in self._protocols:
            algs.extend([
                Secur32Const.CALG_SHA512,
                Secur32Const.CALG_SHA384,
                Secur32Const.CALG_SHA256,
            ])

        alg_array = new(secur32, 'ALG_ID[%s]' % len(algs))
        for index, alg in enumerate(algs):
            alg_array[index] = alg

        flags = Secur32Const.SCH_USE_STRONG_CRYPTO | Secur32Const.SCH_CRED_NO_DEFAULT_CREDS
        if not self._manual_validation and not self._extra_trust_roots:
            flags |= Secur32Const.SCH_CRED_AUTO_CRED_VALIDATION
        else:
            flags |= Secur32Const.SCH_CRED_MANUAL_CRED_VALIDATION

        schannel_cred_pointer = struct(secur32, 'SCHANNEL_CRED')
        schannel_cred = unwrap(schannel_cred_pointer)

        schannel_cred.dwVersion = Secur32Const.SCHANNEL_CRED_VERSION
        schannel_cred.cCreds = 0
        schannel_cred.paCred = null()
        schannel_cred.hRootStore = null()
        schannel_cred.cMappers = 0
        schannel_cred.aphMappers = null()
        schannel_cred.cSupportedAlgs = len(alg_array)
        schannel_cred.palgSupportedAlgs = alg_array
        schannel_cred.grbitEnabledProtocols = protocol_bit_mask
        schannel_cred.dwMinimumCipherStrength = 0
        schannel_cred.dwMaximumCipherStrength = 0
        # Default session lifetime is 10 hours
        schannel_cred.dwSessionLifespan = 0
        schannel_cred.dwFlags = flags
        schannel_cred.dwCredFormat = 0

        cred_handle_pointer = new(secur32, 'CredHandle *')

        result = secur32.AcquireCredentialsHandleW(
            null(),
            Secur32Const.UNISP_NAME,
            Secur32Const.SECPKG_CRED_OUTBOUND,
            null(),
            schannel_cred_pointer,
            null(),
            null(),
            cred_handle_pointer,
            null()
        )
        handle_error(result)

        self._credentials_handle = cred_handle_pointer

    def __del__(self):
        if self._credentials_handle:
            result = secur32.FreeCredentialsHandle(self._credentials_handle)
            handle_error(result)
            self._credentials_handle = None


class TLSSocket(object):
    """
    A wrapper around a socket.socket that adds TLS
    """

    _socket = None
    _session = None

    _context_handle_pointer = None
    _context_flags = None
    _hostname = None

    _header_size = None
    _message_size = None
    _trailer_size = None

    _received_bytes = None
    _decrypted_bytes = None

    _encrypt_desc = None
    _encrypt_buffers = None
    _encrypt_data_buffer = None

    _decrypt_desc = None
    _decrypt_buffers = None
    _decrypt_data_buffer = None

    _certificate = None
    _intermediates = None

    _protocol = None
    _cipher_suite = None
    _compression = None
    _session_id = None
    _session_ticket = None

    _remote_closed = False

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

        # Since we don't create the socket connection here, we can't try to
        # reconnect with a lower version of the TLS protocol, so we just
        # move the data to public exception type TLSVerificationError()
        try:
            new_socket._handshake()
        except (_TLSDowngradeError) as e:
            new_e = TLSVerificationError(e.message, e.certificate)
            raise new_e
        except (_TLSRetryError) as e:
            new_e = TLSError(e.message)
            raise new_e

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

        self._received_bytes = b''
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

            try:
                self._handshake()
            except (_TLSDowngradeError):
                self.close()
                new_session = TLSSession(
                    session._protocols - set(['TLSv1.2']),
                    session._manual_validation,
                    session._extra_trust_roots
                )
                session.__del__()
                self._received_bytes = b''
                self._session = new_session
                self._socket = socket_.create_connection((address, port), timeout)
                self._socket.settimeout(timeout)
                self._handshake()
            except (_TLSRetryError):
                self._received_bytes = b''
                self._socket = socket_.create_connection((address, port), timeout)
                self._socket.settimeout(timeout)
                self._handshake()

    def _create_buffers(self, number):
        """
        Creates a SecBufferDesc struct and contained SecBuffer structs

        :param number:
            The number of contains SecBuffer objects to create

        :return:
            A tuple of (SecBufferDesc pointer, SecBuffer array)
        """

        buffers = new(secur32, 'SecBuffer[%d]' % number)

        for index in range(0, number):
            buffers[index].cbBuffer = 0
            buffers[index].BufferType = Secur32Const.SECBUFFER_EMPTY
            buffers[index].pvBuffer = null()

        sec_buffer_desc_pointer = struct(secur32, 'SecBufferDesc')
        sec_buffer_desc = unwrap(sec_buffer_desc_pointer)

        sec_buffer_desc.ulVersion = Secur32Const.SECBUFFER_VERSION
        sec_buffer_desc.cBuffers = number
        sec_buffer_desc.pBuffers = buffers

        return (sec_buffer_desc_pointer, buffers)

    def _extra_trust_root_validation(self):
        """
        Manually invoked windows certificate chain builder and verification
        step when there are extra trust roots to include in the search process
        """

        store = None
        cert_chain_context_pointer = None

        try:
            # We set up an in-memory store to pass as an extra store to grab
            # certificates from when performing the verification
            store = crypt32.CertOpenStore(
                Crypt32Const.CERT_STORE_PROV_MEMORY,
                Crypt32Const.X509_ASN_ENCODING,
                null(),
                0,
                null()
            )
            if is_null(store):
                handle_crypt32_error(0)

            cert_hashes = set()
            for cert in self._session._extra_trust_roots:
                cert_data = cert.dump()
                result = crypt32.CertAddEncodedCertificateToStore(
                    store,
                    Crypt32Const.X509_ASN_ENCODING,
                    cert_data,
                    len(cert_data),
                    Crypt32Const.CERT_STORE_ADD_USE_EXISTING,
                    null()
                )
                if not result:
                    handle_crypt32_error(0)
                cert_hashes.add(cert.sha256)

            cert_context_pointer_pointer = new(crypt32, 'PCERT_CONTEXT *')
            result = secur32.QueryContextAttributesW(
                self._context_handle_pointer,
                Secur32Const.SECPKG_ATTR_REMOTE_CERT_CONTEXT,
                cert_context_pointer_pointer
            )
            handle_error(result)

            cert_context_pointer = unwrap(cert_context_pointer_pointer)
            cert_context_pointer = cast(crypt32, 'PCERT_CONTEXT', cert_context_pointer)

            # We have to do a funky shuffle here because FILETIME from kernel32
            # is different than FILETIME from crypt32 when using cffi. If we
            # overwrite the "now_pointer" variable, cffi releases the backing
            # memory and we end up getting a validation error about certificate
            # expiration time.
            orig_now_pointer = new(kernel32, 'FILETIME *')
            kernel32.GetSystemTimeAsFileTime(orig_now_pointer)
            now_pointer = cast(crypt32, 'FILETIME *', orig_now_pointer)

            usage_identifiers = new(crypt32, 'char *[3]')
            usage_identifiers[0] = cast(crypt32, 'char *', Crypt32Const.PKIX_KP_SERVER_AUTH)
            usage_identifiers[1] = cast(crypt32, 'char *', Crypt32Const.SERVER_GATED_CRYPTO)
            usage_identifiers[2] = cast(crypt32, 'char *', Crypt32Const.SGC_NETSCAPE)

            cert_enhkey_usage_pointer = struct(crypt32, 'CERT_ENHKEY_USAGE')
            cert_enhkey_usage = unwrap(cert_enhkey_usage_pointer)
            cert_enhkey_usage.cUsageIdentifier = 3
            cert_enhkey_usage.rgpszUsageIdentifier = cast(crypt32, 'char **', usage_identifiers)

            cert_usage_match_pointer = struct(crypt32, 'CERT_USAGE_MATCH')
            cert_usage_match = unwrap(cert_usage_match_pointer)
            cert_usage_match.dwType = Crypt32Const.USAGE_MATCH_TYPE_OR
            cert_usage_match.Usage = cert_enhkey_usage

            cert_chain_para_pointer = struct(crypt32, 'CERT_CHAIN_PARA')
            cert_chain_para = unwrap(cert_chain_para_pointer)
            cert_chain_para.RequestedUsage = cert_usage_match
            cert_chain_para_size = sizeof(crypt32, cert_chain_para)
            cert_chain_para.cbSize = cert_chain_para_size

            cert_chain_context_pointer_pointer = new(crypt32, 'PCERT_CHAIN_CONTEXT *')
            result = crypt32.CertGetCertificateChain(
                null(),
                cert_context_pointer,
                now_pointer,
                store,
                cert_chain_para_pointer,
                Crypt32Const.CERT_CHAIN_CACHE_END_CERT | Crypt32Const.CERT_CHAIN_REVOCATION_CHECK_CACHE_ONLY,
                null(),
                cert_chain_context_pointer_pointer
            )
            handle_crypt32_error(result)

            cert_chain_policy_para_flags = Crypt32Const.CERT_CHAIN_POLICY_IGNORE_ALL_REV_UNKNOWN_FLAGS

            cert_chain_context_pointer = unwrap(cert_chain_context_pointer_pointer)

            # Unwrap the chain and if the final element in the chain is one of
            # extra trust roots, set flags so that we trust the certificate even
            # though it is not in the Trusted Roots store
            cert_chain_context = unwrap(cert_chain_context_pointer)
            num_chains = native(int, cert_chain_context.cChain)
            if num_chains == 1:
                first_simple_chain_pointer = unwrap(cert_chain_context.rgpChain)
                first_simple_chain = unwrap(first_simple_chain_pointer)
                num_elements = native(int, first_simple_chain.cElement)
                last_element_pointer = first_simple_chain.rgpElement[num_elements - 1]
                last_element = unwrap(last_element_pointer)
                last_element_cert = unwrap(last_element.pCertContext)
                last_element_cert_data = bytes_from_buffer(
                    last_element_cert.pbCertEncoded,
                    native(int, last_element_cert.cbCertEncoded)
                )
                last_cert = Asn1Certificate.load(last_element_cert_data)
                if last_cert.sha256 in cert_hashes:
                    cert_chain_policy_para_flags |= Crypt32Const.CERT_CHAIN_POLICY_ALLOW_UNKNOWN_CA_FLAG

            ssl_extra_cert_chain_policy_para_pointer = struct(crypt32, 'SSL_EXTRA_CERT_CHAIN_POLICY_PARA')
            ssl_extra_cert_chain_policy_para = unwrap(ssl_extra_cert_chain_policy_para_pointer)
            ssl_extra_cert_chain_policy_para.cbSize = sizeof(crypt32, ssl_extra_cert_chain_policy_para)
            ssl_extra_cert_chain_policy_para.dwAuthType = Crypt32Const.AUTHTYPE_SERVER
            ssl_extra_cert_chain_policy_para.fdwChecks = 0
            ssl_extra_cert_chain_policy_para.pwszServerName = cast(
                crypt32,
                'wchar_t *',
                buffer_from_unicode(self._hostname)
            )

            cert_chain_policy_para_pointer = struct(crypt32, 'CERT_CHAIN_POLICY_PARA')
            cert_chain_policy_para = unwrap(cert_chain_policy_para_pointer)
            cert_chain_policy_para.cbSize = sizeof(crypt32, cert_chain_policy_para)
            cert_chain_policy_para.dwFlags = cert_chain_policy_para_flags
            cert_chain_policy_para.pvExtraPolicyPara = cast(crypt32, 'void *', ssl_extra_cert_chain_policy_para_pointer)

            cert_chain_policy_status_pointer = struct(crypt32, 'CERT_CHAIN_POLICY_STATUS')
            cert_chain_policy_status = unwrap(cert_chain_policy_status_pointer)
            cert_chain_policy_status.cbSize = sizeof(crypt32, cert_chain_policy_status)

            result = crypt32.CertVerifyCertificateChainPolicy(
                Crypt32Const.CERT_CHAIN_POLICY_SSL,
                cert_chain_context_pointer,
                cert_chain_policy_para_pointer,
                cert_chain_policy_status_pointer
            )
            handle_crypt32_error(result)

            cert_context = unwrap(cert_context_pointer)
            cert_data = bytes_from_buffer(cert_context.pbCertEncoded, native(int, cert_context.cbCertEncoded))
            cert = Asn1Certificate.load(cert_data)

            error = cert_chain_policy_status.dwError
            if error:
                if error == Crypt32Const.CERT_E_EXPIRED:
                    raise_expired_not_yet_valid(cert)
                if error == Crypt32Const.CERT_E_UNTRUSTEDROOT:
                    oscrypto_cert = load_certificate(cert)
                    if oscrypto_cert.self_signed:
                        raise_self_signed(cert)
                    else:
                        raise_no_issuer(cert)
                if error == Crypt32Const.CERT_E_CN_NO_MATCH:
                    raise_hostname(cert, self._hostname)

                if error == Crypt32Const.TRUST_E_CERT_SIGNATURE:
                    raise_weak_signature(cert)

                if error == Crypt32Const.CRYPT_E_REVOKED:
                    raise_revoked(cert)

                raise_verification(cert)

            if cert.hash_algo in set(['md5', 'md2']):
                raise_weak_signature(cert)

        finally:
            if store:
                crypt32.CertCloseStore(store, 0)
            if cert_chain_context_pointer:
                crypt32.CertFreeCertificateChain(cert_chain_context_pointer)

    def _handshake(self, renegotiate=False):
        """
        Perform an initial TLS handshake, or a renegotiation

        :param renegotiate:
            If the handshake is for a renegotiation
        """

        in_buffers = None
        out_buffers = None
        new_context_handle_pointer = None

        try:
            if renegotiate:
                temp_context_handle_pointer = self._context_handle_pointer
            else:
                new_context_handle_pointer = new(secur32, 'CtxtHandle *')
                temp_context_handle_pointer = new_context_handle_pointer

            requested_flags = {
                Secur32Const.ISC_REQ_REPLAY_DETECT: 'replay detection',
                Secur32Const.ISC_REQ_SEQUENCE_DETECT: 'sequence detection',
                Secur32Const.ISC_REQ_CONFIDENTIALITY: 'confidentiality',
                Secur32Const.ISC_REQ_ALLOCATE_MEMORY: 'memory allocation',
                Secur32Const.ISC_REQ_INTEGRITY: 'integrity',
                Secur32Const.ISC_REQ_STREAM: 'stream orientation',
                Secur32Const.ISC_REQ_USE_SUPPLIED_CREDS: 'disable automatic client auth',
            }

            self._context_flags = 0
            for flag in requested_flags:
                self._context_flags |= flag

            in_sec_buffer_desc_pointer, in_buffers = self._create_buffers(2)
            in_buffers[0].BufferType = Secur32Const.SECBUFFER_TOKEN

            out_sec_buffer_desc_pointer, out_buffers = self._create_buffers(2)
            out_buffers[0].BufferType = Secur32Const.SECBUFFER_TOKEN
            out_buffers[1].BufferType = Secur32Const.SECBUFFER_ALERT

            output_context_flags_pointer = new(secur32, 'ULONG *')

            if renegotiate:
                first_handle = temp_context_handle_pointer
                second_handle = null()
            else:
                first_handle = null()
                second_handle = temp_context_handle_pointer

            result = secur32.InitializeSecurityContextW(
                self._session._credentials_handle,
                first_handle,
                self._hostname,
                self._context_flags,
                0,
                0,
                null(),
                0,
                second_handle,
                out_sec_buffer_desc_pointer,
                output_context_flags_pointer,
                null()
            )
            if result not in set([Secur32Const.SEC_E_OK, Secur32Const.SEC_I_CONTINUE_NEEDED]):
                handle_error(result, TLSError)

            if not renegotiate:
                temp_context_handle_pointer = second_handle
            else:
                temp_context_handle_pointer = first_handle

            handshake_server_bytes = b''
            handshake_client_bytes = b''

            if out_buffers[0].cbBuffer > 0:
                token = bytes_from_buffer(out_buffers[0].pvBuffer, out_buffers[0].cbBuffer)
                handshake_client_bytes += token
                self._socket.send(token)
                out_buffers[0].cbBuffer = 0
                secur32.FreeContextBuffer(out_buffers[0].pvBuffer)
                out_buffers[0].pvBuffer = null()

            in_data_buffer = buffer_from_bytes(32768)
            in_buffers[0].pvBuffer = cast(secur32, 'BYTE *', in_data_buffer)

            bytes_read = b''
            while result != Secur32Const.SEC_E_OK:
                try:
                    fail_late = False
                    bytes_read = self._socket.recv(8192)
                    if bytes_read == b'':
                        raise_disconnection()
                except (socket_error_cls):
                    fail_late = True
                handshake_server_bytes += bytes_read
                self._received_bytes += bytes_read

                in_buffers[0].cbBuffer = len(self._received_bytes)
                write_to_buffer(in_data_buffer, self._received_bytes)

                result = secur32.InitializeSecurityContextW(
                    self._session._credentials_handle,
                    temp_context_handle_pointer,
                    self._hostname,
                    self._context_flags,
                    0,
                    0,
                    in_sec_buffer_desc_pointer,
                    0,
                    null(),
                    out_sec_buffer_desc_pointer,
                    output_context_flags_pointer,
                    null()
                )

                if result == Secur32Const.SEC_E_INCOMPLETE_MESSAGE:
                    in_buffers[0].BufferType = Secur32Const.SECBUFFER_TOKEN
                    # Windows 10 seems to fill the second input buffer with
                    # a BufferType of SECBUFFER_MISSING (4), which if not
                    # cleared causes the handshake to fail.
                    if in_buffers[1].BufferType != Secur32Const.SECBUFFER_EMPTY:
                        in_buffers[1].BufferType = Secur32Const.SECBUFFER_EMPTY
                        in_buffers[1].cbBuffer = 0
                        if not is_null(in_buffers[1].pvBuffer):
                            secur32.FreeContextBuffer(in_buffers[1].pvBuffer)
                            in_buffers[1].pvBuffer = null()

                    if fail_late:
                        raise_disconnection()

                    continue

                if result == Secur32Const.SEC_E_ILLEGAL_MESSAGE:
                    if detect_client_auth_request(handshake_server_bytes):
                        raise_client_auth()
                    alert_info = parse_alert(handshake_server_bytes)
                    if alert_info and alert_info == (2, 70):
                        raise_protocol_version()
                    raise_handshake()

                if result == Secur32Const.SEC_E_WRONG_PRINCIPAL:
                    chain = extract_chain(handshake_server_bytes)
                    raise_hostname(chain[0], self._hostname)

                if result == Secur32Const.SEC_E_CERT_EXPIRED:
                    chain = extract_chain(handshake_server_bytes)
                    raise_expired_not_yet_valid(chain[0])

                if result == Secur32Const.SEC_E_UNTRUSTED_ROOT:
                    chain = extract_chain(handshake_server_bytes)
                    cert = chain[0]
                    oscrypto_cert = load_certificate(cert)
                    if not oscrypto_cert.self_signed:
                        raise_no_issuer(cert)
                    raise_self_signed(cert)

                if result == Secur32Const.SEC_E_INTERNAL_ERROR:
                    if get_dh_params_length(handshake_server_bytes) < 1024:
                        raise_dh_params()

                if result == Secur32Const.SEC_I_INCOMPLETE_CREDENTIALS:
                    raise_client_auth()

                if result == Crypt32Const.TRUST_E_CERT_SIGNATURE:
                    raise_weak_signature(cert)

                if result == Secur32Const.SEC_E_INVALID_TOKEN:
                    # If an alert it present, there may have been a handshake
                    # error due to the server using a certificate path with a
                    # trust root using MD2 or MD5 combined with TLS 1.2. To
                    # work around this, if the user allows anything other than
                    # TLS 1.2, we just remove it from the acceptable protocols
                    # and try again.
                    if out_buffers[1].cbBuffer > 0:
                        alert_bytes = bytes_from_buffer(out_buffers[1].pvBuffer, out_buffers[1].cbBuffer)
                        handshake_client_bytes += alert_bytes
                        alert_number = alert_bytes[6:7]
                        if alert_number == b'\x28' or alert_number == b'\x2b':
                            if 'TLSv1.2' in self._session._protocols and len(self._session._protocols) > 1:
                                chain = extract_chain(handshake_server_bytes)
                                raise _TLSDowngradeError(
                                    'Server certificate verification failed - weak certificate signature algorithm',
                                    chain[0]
                                )
                    if detect_client_auth_request(handshake_server_bytes):
                        raise_client_auth()
                    if detect_other_protocol(handshake_server_bytes):
                        raise_protocol_error(handshake_server_bytes)
                    raise_handshake()

                # These are semi-common errors with TLSv1.2 on Windows 7 an 8
                # that appears to be due to poor handling of the
                # ServerKeyExchange for DHE_RSA cipher suites. The solution
                # is to retry the handshake.
                if result == Secur32Const.SEC_E_BUFFER_TOO_SMALL or result == Secur32Const.SEC_E_MESSAGE_ALTERED:
                    if 'TLSv1.2' in self._session._protocols:
                        raise _TLSRetryError('TLS handshake failed')

                if fail_late:
                    raise_disconnection()

                if result == Secur32Const.SEC_E_INVALID_PARAMETER:
                    if get_dh_params_length(handshake_server_bytes) < 1024:
                        raise_dh_params()

                if result not in set([Secur32Const.SEC_E_OK, Secur32Const.SEC_I_CONTINUE_NEEDED]):
                    handle_error(result, TLSError)

                if out_buffers[0].cbBuffer > 0:
                    token = bytes_from_buffer(out_buffers[0].pvBuffer, out_buffers[0].cbBuffer)
                    handshake_client_bytes += token
                    self._socket.send(token)
                    out_buffers[0].cbBuffer = 0
                    secur32.FreeContextBuffer(out_buffers[0].pvBuffer)
                    out_buffers[0].pvBuffer = null()

                if in_buffers[1].BufferType == Secur32Const.SECBUFFER_EXTRA:
                    extra_amount = in_buffers[1].cbBuffer
                    self._received_bytes = self._received_bytes[-extra_amount:]
                    in_buffers[1].BufferType = Secur32Const.SECBUFFER_EMPTY
                    in_buffers[1].cbBuffer = 0
                    secur32.FreeContextBuffer(in_buffers[1].pvBuffer)
                    in_buffers[1].pvBuffer = null()

                    # The handshake is complete, so discard any extra bytes
                    if result == Secur32Const.SEC_E_OK:
                        handshake_server_bytes = handshake_server_bytes[-extra_amount:]

                else:
                    self._received_bytes = b''

            connection_info_pointer = struct(secur32, 'SecPkgContext_ConnectionInfo')
            result = secur32.QueryContextAttributesW(
                temp_context_handle_pointer,
                Secur32Const.SECPKG_ATTR_CONNECTION_INFO,
                connection_info_pointer
            )
            handle_error(result, TLSError)

            connection_info = unwrap(connection_info_pointer)

            self._protocol = {
                Secur32Const.SP_PROT_SSL2_CLIENT: 'SSLv2',
                Secur32Const.SP_PROT_SSL3_CLIENT: 'SSLv3',
                Secur32Const.SP_PROT_TLS1_CLIENT: 'TLSv1',
                Secur32Const.SP_PROT_TLS1_1_CLIENT: 'TLSv1.1',
                Secur32Const.SP_PROT_TLS1_2_CLIENT: 'TLSv1.2',
            }.get(native(int, connection_info.dwProtocol), str_cls(connection_info.dwProtocol))

            if self._protocol in set(['SSLv3', 'TLSv1', 'TLSv1.1', 'TLSv1.2']):
                session_info = parse_session_info(handshake_server_bytes, handshake_client_bytes)
                self._cipher_suite = session_info['cipher_suite']
                self._compression = session_info['compression']
                self._session_id = session_info['session_id']
                self._session_ticket = session_info['session_ticket']

            output_context_flags = deref(output_context_flags_pointer)

            for flag in requested_flags:
                if (flag | output_context_flags) == 0:
                    raise OSError(pretty_message(
                        '''
                        Unable to obtain a credential context with the property %s
                        ''',
                        requested_flags[flag]
                    ))

            if not renegotiate:
                self._context_handle_pointer = temp_context_handle_pointer
                new_context_handle_pointer = None

                stream_sizes_pointer = struct(secur32, 'SecPkgContext_StreamSizes')
                result = secur32.QueryContextAttributesW(
                    self._context_handle_pointer,
                    Secur32Const.SECPKG_ATTR_STREAM_SIZES,
                    stream_sizes_pointer
                )
                handle_error(result)

                stream_sizes = unwrap(stream_sizes_pointer)
                self._header_size = native(int, stream_sizes.cbHeader)
                self._message_size = native(int, stream_sizes.cbMaximumMessage)
                self._trailer_size = native(int, stream_sizes.cbTrailer)
                self._buffer_size = self._header_size + self._message_size + self._trailer_size

            if self._session._extra_trust_roots:
                self._extra_trust_root_validation()

        except (OSError, socket_.error):
            self.close()

            raise

        finally:
            if out_buffers:
                if not is_null(out_buffers[0].pvBuffer):
                    secur32.FreeContextBuffer(out_buffers[0].pvBuffer)
                if not is_null(out_buffers[1].pvBuffer):
                    secur32.FreeContextBuffer(out_buffers[1].pvBuffer)
            if new_context_handle_pointer:
                secur32.DeleteSecurityContext(new_context_handle_pointer)

    def read(self, max_length):
        """
        Reads data from the TLS-wrapped socket

        :param max_length:
            The number of bytes to read

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

        if self._context_handle_pointer is None:

            # Allow the user to read any remaining decrypted data
            if self._decrypted_bytes != b'':
                output = self._decrypted_bytes[0:max_length]
                self._decrypted_bytes = self._decrypted_bytes[max_length:]
                return output

            self._raise_closed()

        # The first time read is called, set up a single contiguous buffer that
        # it used by DecryptMessage() to populate the three output buffers.
        # Since we are creating the buffer, we do not need to free it other
        # than allowing Python to GC it once this object is GCed.
        if not self._decrypt_data_buffer:
            self._decrypt_data_buffer = buffer_from_bytes(self._buffer_size)
            self._decrypt_desc, self._decrypt_buffers = self._create_buffers(4)
            self._decrypt_buffers[0].BufferType = Secur32Const.SECBUFFER_DATA
            self._decrypt_buffers[0].pvBuffer = cast(secur32, 'BYTE *', self._decrypt_data_buffer)

        to_recv = max(max_length, self._buffer_size)

        # These variables are set to reduce dict access and function calls
        # in the read loop. Also makes the code easier to read.
        null_value = null()
        buf0 = self._decrypt_buffers[0]
        buf1 = self._decrypt_buffers[1]
        buf2 = self._decrypt_buffers[2]
        buf3 = self._decrypt_buffers[3]

        def _reset_buffers():
            buf0.BufferType = Secur32Const.SECBUFFER_DATA
            buf0.pvBuffer = cast(secur32, 'BYTE *', self._decrypt_data_buffer)
            buf0.cbBuffer = 0

            buf1.BufferType = Secur32Const.SECBUFFER_EMPTY
            buf1.pvBuffer = null_value
            buf1.cbBuffer = 0

            buf2.BufferType = Secur32Const.SECBUFFER_EMPTY
            buf2.pvBuffer = null_value
            buf2.cbBuffer = 0

            buf3.BufferType = Secur32Const.SECBUFFER_EMPTY
            buf3.pvBuffer = null_value
            buf3.cbBuffer = 0

        output = self._decrypted_bytes
        output_len = len(output)

        self._decrypted_bytes = b''

        # Don't block if we have buffered data available
        if output_len > 0 and not self.select_read(0):
            self._decrypted_bytes = b''
            return output

        # This read loop will only be run if there wasn't enough
        # buffered data to fulfill the requested max_length
        do_read = len(self._received_bytes) == 0

        while output_len < max_length:
            if do_read:
                self._received_bytes += self._socket.recv(to_recv)
                if len(self._received_bytes) == 0:
                    raise_disconnection()

            data_len = min(len(self._received_bytes), self._buffer_size)
            if data_len == 0:
                break
            self._decrypt_buffers[0].cbBuffer = data_len
            write_to_buffer(self._decrypt_data_buffer, self._received_bytes[0:data_len])

            result = secur32.DecryptMessage(
                self._context_handle_pointer,
                self._decrypt_desc,
                0,
                null()
            )

            do_read = False

            if result == Secur32Const.SEC_E_INCOMPLETE_MESSAGE:
                _reset_buffers()
                do_read = True
                continue

            elif result == Secur32Const.SEC_I_CONTEXT_EXPIRED:
                self._remote_closed = True
                self.shutdown()
                break

            elif result == Secur32Const.SEC_I_RENEGOTIATE:
                self._handshake(renegotiate=True)
                return self.read(max_length)

            elif result != Secur32Const.SEC_E_OK:
                handle_error(result, TLSError)

            valid_buffer_types = set([
                Secur32Const.SECBUFFER_EMPTY,
                Secur32Const.SECBUFFER_STREAM_HEADER,
                Secur32Const.SECBUFFER_STREAM_TRAILER
            ])
            extra_amount = None
            for buf in (buf0, buf1, buf2, buf3):
                buffer_type = buf.BufferType
                if buffer_type == Secur32Const.SECBUFFER_DATA:
                    output += bytes_from_buffer(buf.pvBuffer, buf.cbBuffer)
                    output_len = len(output)
                elif buffer_type == Secur32Const.SECBUFFER_EXTRA:
                    extra_amount = native(int, buf.cbBuffer)
                elif buffer_type not in valid_buffer_types:
                    raise OSError(pretty_message(
                        '''
                        Unexpected decrypt output buffer of type %s
                        ''',
                        buffer_type
                    ))

            if extra_amount:
                self._received_bytes = self._received_bytes[data_len - extra_amount:]
            else:
                self._received_bytes = self._received_bytes[data_len:]

            # Here we reset the structs for the next call to DecryptMessage()
            _reset_buffers()

            # If we have read something, but there is nothing left to read, we
            # break so that we don't block for longer than necessary
            if self.select_read(0):
                do_read = True

            if not do_read and len(self._received_bytes) == 0:
                break

        # If the output is more than we requested (because data is decrypted in
        # blocks), we save the extra in a buffer
        if len(output) > max_length:
            self._decrypted_bytes = output[max_length:]
            output = output[0:max_length]

        return output

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
        Reads data from the socket until a marker is found. Data read may
        include data beyond the marker.

        :param marker:
            A byte string or regex object from re.compile(). Used to determine
            when to stop reading. Regex objects are more inefficient since
            they must scan the entire byte string of read data each time data
            is read off the socket.

        :return:
            A byte string of the data read
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
                chunk = self.read(8192)

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

        if self._context_handle_pointer is None:
            self._raise_closed()

        if not self._encrypt_data_buffer:
            self._encrypt_data_buffer = buffer_from_bytes(self._header_size + self._message_size + self._trailer_size)
            self._encrypt_desc, self._encrypt_buffers = self._create_buffers(4)

            self._encrypt_buffers[0].BufferType = Secur32Const.SECBUFFER_STREAM_HEADER
            self._encrypt_buffers[0].cbBuffer = self._header_size
            self._encrypt_buffers[0].pvBuffer = cast(secur32, 'BYTE *', self._encrypt_data_buffer)

            self._encrypt_buffers[1].BufferType = Secur32Const.SECBUFFER_DATA
            self._encrypt_buffers[1].pvBuffer = ref(self._encrypt_data_buffer, self._header_size)

            self._encrypt_buffers[2].BufferType = Secur32Const.SECBUFFER_STREAM_TRAILER
            self._encrypt_buffers[2].cbBuffer = self._trailer_size
            self._encrypt_buffers[2].pvBuffer = ref(self._encrypt_data_buffer, self._header_size + self._message_size)

        while len(data) > 0:
            to_write = min(len(data), self._message_size)
            write_to_buffer(self._encrypt_data_buffer, data[0:to_write], self._header_size)

            self._encrypt_buffers[1].cbBuffer = to_write
            self._encrypt_buffers[2].pvBuffer = ref(self._encrypt_data_buffer, self._header_size + to_write)

            result = secur32.EncryptMessage(
                self._context_handle_pointer,
                0,
                self._encrypt_desc,
                0
            )

            if result != Secur32Const.SEC_E_OK:
                handle_error(result, TLSError)

            to_send = native(int, self._encrypt_buffers[0].cbBuffer)
            to_send += native(int, self._encrypt_buffers[1].cbBuffer)
            to_send += native(int, self._encrypt_buffers[2].cbBuffer)
            try:
                self._socket.send(bytes_from_buffer(self._encrypt_data_buffer, to_send))
            except (socket_.error) as e:
                if e.errno == 10053:
                    raise_disconnection()
                raise

            data = data[to_send:]

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

    def shutdown(self):
        """
        Shuts down the TLS session and then shuts down the underlying socket

        :raises:
            OSError - when an error is returned by the OS crypto library
        """

        if self._context_handle_pointer is None:
            return

        out_buffers = None
        try:
            # ApplyControlToken fails with SEC_E_UNSUPPORTED_FUNCTION
            # when called on Windows 7
            if _win_version_info >= (6, 2):
                buffers = new(secur32, 'SecBuffer[1]')

                # This is a SCHANNEL_SHUTDOWN token (DWORD of 1)
                buffers[0].cbBuffer = 4
                buffers[0].BufferType = Secur32Const.SECBUFFER_TOKEN
                buffers[0].pvBuffer = cast(secur32, 'BYTE *', buffer_from_bytes(b'\x01\x00\x00\x00'))

                sec_buffer_desc_pointer = struct(secur32, 'SecBufferDesc')
                sec_buffer_desc = unwrap(sec_buffer_desc_pointer)

                sec_buffer_desc.ulVersion = Secur32Const.SECBUFFER_VERSION
                sec_buffer_desc.cBuffers = 1
                sec_buffer_desc.pBuffers = buffers

                result = secur32.ApplyControlToken(self._context_handle_pointer, sec_buffer_desc_pointer)
                handle_error(result, TLSError)

            out_sec_buffer_desc_pointer, out_buffers = self._create_buffers(2)
            out_buffers[0].BufferType = Secur32Const.SECBUFFER_TOKEN
            out_buffers[1].BufferType = Secur32Const.SECBUFFER_ALERT

            output_context_flags_pointer = new(secur32, 'ULONG *')

            result = secur32.InitializeSecurityContextW(
                self._session._credentials_handle,
                self._context_handle_pointer,
                self._hostname,
                self._context_flags,
                0,
                0,
                null(),
                0,
                null(),
                out_sec_buffer_desc_pointer,
                output_context_flags_pointer,
                null()
            )
            acceptable_results = set([
                Secur32Const.SEC_E_OK,
                Secur32Const.SEC_E_CONTEXT_EXPIRED,
                Secur32Const.SEC_I_CONTINUE_NEEDED
            ])
            if result not in acceptable_results:
                handle_error(result, TLSError)

            token = bytes_from_buffer(out_buffers[0].pvBuffer, out_buffers[0].cbBuffer)
            try:
                # If there is an error sending the shutdown, ignore it since the
                # connection is likely gone at this point
                self._socket.send(token)
            except (socket_.error):
                pass

        finally:
            if out_buffers:
                if not is_null(out_buffers[0].pvBuffer):
                    secur32.FreeContextBuffer(out_buffers[0].pvBuffer)
                if not is_null(out_buffers[1].pvBuffer):
                    secur32.FreeContextBuffer(out_buffers[1].pvBuffer)

            secur32.DeleteSecurityContext(self._context_handle_pointer)
            self._context_handle_pointer = None

            try:
                self._socket.shutdown(socket_.SHUT_RDWR)
            except (socket_.error):
                pass

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

        cert_context_pointer_pointer = new(crypt32, 'CERT_CONTEXT **')
        result = secur32.QueryContextAttributesW(
            self._context_handle_pointer,
            Secur32Const.SECPKG_ATTR_REMOTE_CERT_CONTEXT,
            cert_context_pointer_pointer
        )
        handle_error(result, TLSError)

        cert_context_pointer = unwrap(cert_context_pointer_pointer)
        cert_context_pointer = cast(crypt32, 'CERT_CONTEXT *', cert_context_pointer)
        cert_context = unwrap(cert_context_pointer)

        cert_data = bytes_from_buffer(cert_context.pbCertEncoded, native(int, cert_context.cbCertEncoded))
        self._certificate = Asn1Certificate.load(cert_data)

        self._intermediates = []

        store_handle = None
        try:
            store_handle = cert_context.hCertStore
            context_pointer = crypt32.CertEnumCertificatesInStore(store_handle, null())
            while not is_null(context_pointer):
                context = unwrap(context_pointer)
                data = bytes_from_buffer(context.pbCertEncoded, native(int, context.cbCertEncoded))
                # The cert store seems to include the end-entity certificate as
                # the last entry, but we already have that from the struct.
                if data != cert_data:
                    self._intermediates.append(Asn1Certificate.load(data))
                context_pointer = crypt32.CertEnumCertificatesInStore(store_handle, context_pointer)

        finally:
            if store_handle:
                crypt32.CertCloseStore(store_handle, 0)

    def _raise_closed(self):
        """
        Raises an exception describing if the local or remote end closed the
        connection
        """

        if self._remote_closed:
            raise TLSGracefulDisconnectError('The remote end closed the connection')
        else:
            raise TLSDisconnectError('The connection was already closed')

    @property
    def certificate(self):
        """
        An asn1crypto.x509.Certificate object of the end-entity certificate
        presented by the server
        """

        if self._context_handle_pointer is None:
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

        if self._context_handle_pointer is None:
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

        if self._context_handle_pointer is None:
            self._raise_closed()

        return self._socket

    def __del__(self):
        self.close()
