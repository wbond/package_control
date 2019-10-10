# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from .. import ffi
from ._decode import _try_decode
from ..errors import TLSError
from .._types import str_cls

if ffi() == 'cffi':
    from ._secur32_cffi import secur32, get_error
else:
    from ._secur32_ctypes import secur32, get_error


__all__ = [
    'handle_error',
    'secur32',
    'Secur32Const',
]


def handle_error(result, exception_class=None):
    """
    Extracts the last Windows error message into a python unicode string

    :param result:
        A function result, 0 or None indicates failure

    :param exception_class:
        The exception class to use for the exception if an error occurred

    :return:
        A unicode string error message
    """

    if result == 0:
        return

    if result == Secur32Const.SEC_E_OUT_OF_SEQUENCE:
        raise TLSError('A packet was received out of order')

    if result == Secur32Const.SEC_E_MESSAGE_ALTERED:
        raise TLSError('A packet was received altered')

    if result == Secur32Const.SEC_E_CONTEXT_EXPIRED:
        raise TLSError('The TLS session expired')

    _, error_string = get_error()

    if not isinstance(error_string, str_cls):
        error_string = _try_decode(error_string)

    if exception_class is None:
        exception_class = OSError

    raise exception_class(('SECURITY_STATUS error 0x%0.2X: ' % result) + error_string)


class Secur32Const():
    SCHANNEL_CRED_VERSION = 4

    SECPKG_CRED_OUTBOUND = 0x00000002
    UNISP_NAME = "Microsoft Unified Security Protocol Provider"

    SCH_CRED_MANUAL_CRED_VALIDATION = 0x00000008
    SCH_CRED_AUTO_CRED_VALIDATION = 0x00000020
    SCH_USE_STRONG_CRYPTO = 0x00400000
    SCH_CRED_NO_DEFAULT_CREDS = 0x00000010

    SECBUFFER_VERSION = 0

    SEC_E_OK = 0x00000000
    SEC_I_CONTINUE_NEEDED = 0x00090312
    SEC_I_CONTEXT_EXPIRED = 0x00090317
    SEC_I_RENEGOTIATE = 0x00090321
    SEC_E_INCOMPLETE_MESSAGE = 0x80090318
    SEC_E_INVALID_TOKEN = 0x80090308
    SEC_E_OUT_OF_SEQUENCE = 0x8009031
    SEC_E_MESSAGE_ALTERED = 0x8009030F
    SEC_E_CONTEXT_EXPIRED = 0x80090317
    SEC_E_INVALID_PARAMETER = 0x8009035D

    SEC_E_WRONG_PRINCIPAL = 0x80090322  # Domain name mismatch
    SEC_E_UNTRUSTED_ROOT = 0x80090325
    SEC_E_CERT_EXPIRED = 0x80090328
    SEC_E_ILLEGAL_MESSAGE = 0x80090326  # Handshake error
    SEC_E_INTERNAL_ERROR = 0x80090304  # Occurs when DH params are too small
    SEC_E_BUFFER_TOO_SMALL = 0x80090321
    SEC_I_INCOMPLETE_CREDENTIALS = 0x00090320

    ISC_REQ_REPLAY_DETECT = 4
    ISC_REQ_SEQUENCE_DETECT = 8
    ISC_REQ_CONFIDENTIALITY = 16
    ISC_REQ_ALLOCATE_MEMORY = 256
    ISC_REQ_INTEGRITY = 65536
    ISC_REQ_STREAM = 0x00008000
    ISC_REQ_USE_SUPPLIED_CREDS = 0x00000080

    ISC_RET_REPLAY_DETECT = 4
    ISC_RET_SEQUENCE_DETECT = 8
    ISC_RET_CONFIDENTIALITY = 16
    ISC_RET_ALLOCATED_MEMORY = 256
    ISC_RET_INTEGRITY = 65536
    ISC_RET_STREAM = 0x00008000

    SECBUFFER_ALERT = 17
    SECBUFFER_STREAM_HEADER = 7
    SECBUFFER_STREAM_TRAILER = 6
    SECBUFFER_EXTRA = 5
    SECBUFFER_TOKEN = 2
    SECBUFFER_DATA = 1
    SECBUFFER_EMPTY = 0

    SECPKG_ATTR_STREAM_SIZES = 0x04
    SECPKG_ATTR_CONNECTION_INFO = 0x5A
    SECPKG_ATTR_REMOTE_CERT_CONTEXT = 0x53

    SP_PROT_TLS1_2_CLIENT = 0x800
    SP_PROT_TLS1_1_CLIENT = 0x200
    SP_PROT_TLS1_CLIENT = 0x80
    SP_PROT_SSL3_CLIENT = 0x20
    SP_PROT_SSL2_CLIENT = 0x8

    CALG_AES_256 = 0x00006610
    CALG_AES_128 = 0x0000660E
    CALG_3DES = 0x00006603
    CALG_RC4 = 0x00006801
    CALG_RC2 = 0x00006602
    CALG_DES = 0x00006601

    CALG_MD5 = 0x00008003
    CALG_SHA1 = 0x00008004
    CALG_SHA256 = 0x0000800C
    CALG_SHA384 = 0x0000800D
    CALG_SHA512 = 0x0000800E

    CALG_DH_SF = 0x0000AA01
    CALG_DH_EPHEM = 0x0000AA02
    CALG_ECDH = 0x0000AA05
    CALG_ECDHE = 0x0000AE06
    CALG_RSA_KEYX = 0x0000A400

    CALG_RSA_SIGN = 0x00002400
    CALG_ECDSA = 0x00002203
    CALG_DSS_SIGN = 0x00002200
