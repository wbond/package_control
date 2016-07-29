# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from .._ffi import FFIEngineError, is_null, unwrap

try:
    from ._core_foundation_cffi import CoreFoundation, CFHelpers
except (FFIEngineError, ImportError):
    from ._core_foundation_ctypes import CoreFoundation, CFHelpers


_all__ = [
    'CFHelpers',
    'CoreFoundation',
    'handle_cf_error',
]


def handle_cf_error(error_pointer):
    """
    Checks a CFErrorRef and throws an exception if there is an error to report

    :param error_pointer:
        A CFErrorRef

    :raises:
        OSError - when the CFErrorRef contains an error
    """

    if is_null(error_pointer):
        return

    error = unwrap(error_pointer)
    if is_null(error):
        return

    cf_string_domain = CoreFoundation.CFErrorGetDomain(error)
    domain = CFHelpers.cf_string_to_unicode(cf_string_domain)
    CoreFoundation.CFRelease(cf_string_domain)
    num = CoreFoundation.CFErrorGetCode(error)

    cf_string_ref = CoreFoundation.CFErrorCopyDescription(error)
    output = CFHelpers.cf_string_to_unicode(cf_string_ref)
    CoreFoundation.CFRelease(cf_string_ref)

    if output is None:
        if domain == 'NSOSStatusErrorDomain':
            code_map = {
                -2147416010: 'ACL add failed',
                -2147416025: 'ACL base certs not supported',
                -2147416019: 'ACL challenge callback failed',
                -2147416015: 'ACL change failed',
                -2147416012: 'ACL delete failed',
                -2147416017: 'ACL entry tag not found',
                -2147416011: 'ACL replace failed',
                -2147416021: 'ACL subject type not supported',
                -2147415789: 'Algid mismatch',
                -2147415726: 'Already logged in',
                -2147415040: 'Apple add application ACL subject',
                -2147415036: 'Apple invalid key end date',
                -2147415037: 'Apple invalid key start date',
                -2147415039: 'Apple public key incomplete',
                -2147415038: 'Apple signature mismatch',
                -2147415034: 'Apple SSLv2 rollback',
                -2147415802: 'Attach handle busy',
                -2147415731: 'Block size mismatch',
                -2147415722: 'Crypto data callback failed',
                -2147415804: 'Device error',
                -2147415835: 'Device failed',
                -2147415803: 'Device memory error',
                -2147415836: 'Device reset',
                -2147415728: 'Device verify failed',
                -2147416054: 'Function failed',
                -2147416057: 'Function not implemented',
                -2147415807: 'Input length error',
                -2147415837: 'Insufficient client identification',
                -2147416063: 'Internal error',
                -2147416027: 'Invalid access credentials',
                -2147416026: 'Invalid ACL base certs',
                -2147416020: 'Invalid ACL challenge callback',
                -2147416016: 'Invalid ACL edit mode',
                -2147416018: 'Invalid ACL entry tag',
                -2147416022: 'Invalid ACL subject value',
                -2147415759: 'Invalid algorithm',
                -2147415678: 'Invalid attr access credentials',
                -2147415704: 'Invalid attr alg params',
                -2147415686: 'Invalid attr base',
                -2147415738: 'Invalid attr block size',
                -2147415680: 'Invalid attr dl db handle',
                -2147415696: 'Invalid attr effective bits',
                -2147415692: 'Invalid attr end date',
                -2147415752: 'Invalid attr init vector',
                -2147415682: 'Invalid attr iteration count',
                -2147415754: 'Invalid attr key',
                -2147415740: 'Invalid attr key length',
                -2147415700: 'Invalid attr key type',
                -2147415702: 'Invalid attr label',
                -2147415698: 'Invalid attr mode',
                -2147415708: 'Invalid attr output size',
                -2147415748: 'Invalid attr padding',
                -2147415742: 'Invalid attr passphrase',
                -2147415688: 'Invalid attr prime',
                -2147415674: 'Invalid attr private key format',
                -2147415676: 'Invalid attr public key format',
                -2147415746: 'Invalid attr random',
                -2147415706: 'Invalid attr rounds',
                -2147415750: 'Invalid attr salt',
                -2147415744: 'Invalid attr seed',
                -2147415694: 'Invalid attr start date',
                -2147415684: 'Invalid attr subprime',
                -2147415672: 'Invalid attr symmetric key format',
                -2147415690: 'Invalid attr version',
                -2147415670: 'Invalid attr wrapped key format',
                -2147415760: 'Invalid context',
                -2147416000: 'Invalid context handle',
                -2147415976: 'Invalid crypto data',
                -2147415994: 'Invalid data',
                -2147415768: 'Invalid data count',
                -2147415723: 'Invalid digest algorithm',
                -2147416059: 'Invalid input pointer',
                -2147415766: 'Invalid input vector',
                -2147415792: 'Invalid key',
                -2147415780: 'Invalid keyattr mask',
                -2147415782: 'Invalid keyusage mask',
                -2147415790: 'Invalid key class',
                -2147415776: 'Invalid key format',
                -2147415778: 'Invalid key label',
                -2147415783: 'Invalid key pointer',
                -2147415791: 'Invalid key reference',
                -2147415727: 'Invalid login name',
                -2147416014: 'Invalid new ACL entry',
                -2147416013: 'Invalid new ACL owner',
                -2147416058: 'Invalid output pointer',
                -2147415765: 'Invalid output vector',
                -2147415978: 'Invalid passthrough id',
                -2147416060: 'Invalid pointer',
                -2147416024: 'Invalid sample value',
                -2147415733: 'Invalid signature',
                -2147415787: 'Key blob type incorrect',
                -2147415786: 'Key header inconsistent',
                -2147415724: 'Key label already exists',
                -2147415788: 'Key usage incorrect',
                -2147416061: 'Mds error',
                -2147416062: 'Memory error',
                -2147415677: 'Missing attr access credentials',
                -2147415703: 'Missing attr alg params',
                -2147415685: 'Missing attr base',
                -2147415737: 'Missing attr block size',
                -2147415679: 'Missing attr dl db handle',
                -2147415695: 'Missing attr effective bits',
                -2147415691: 'Missing attr end date',
                -2147415751: 'Missing attr init vector',
                -2147415681: 'Missing attr iteration count',
                -2147415753: 'Missing attr key',
                -2147415739: 'Missing attr key length',
                -2147415699: 'Missing attr key type',
                -2147415701: 'Missing attr label',
                -2147415697: 'Missing attr mode',
                -2147415707: 'Missing attr output size',
                -2147415747: 'Missing attr padding',
                -2147415741: 'Missing attr passphrase',
                -2147415687: 'Missing attr prime',
                -2147415673: 'Missing attr private key format',
                -2147415675: 'Missing attr public key format',
                -2147415745: 'Missing attr random',
                -2147415705: 'Missing attr rounds',
                -2147415749: 'Missing attr salt',
                -2147415743: 'Missing attr seed',
                -2147415693: 'Missing attr start date',
                -2147415683: 'Missing attr subprime',
                -2147415671: 'Missing attr symmetric key format',
                -2147415689: 'Missing attr version',
                -2147415669: 'Missing attr wrapped key format',
                -2147415801: 'Not logged in',
                -2147415840: 'No user interaction',
                -2147416029: 'Object ACL not supported',
                -2147416028: 'Object ACL required',
                -2147416030: 'Object manip auth denied',
                -2147416031: 'Object use auth denied',
                -2147416032: 'Operation auth denied',
                -2147416055: 'OS access denied',
                -2147415806: 'Output length error',
                -2147415725: 'Private key already exists',
                -2147415730: 'Private key not found',
                -2147415989: 'Privilege not granted',
                -2147415805: 'Privilege not supported',
                -2147415729: 'Public key inconsistent',
                -2147415732: 'Query size unknown',
                -2147416023: 'Sample value not supported',
                -2147416056: 'Self check failed',
                -2147415838: 'Service not available',
                -2147415736: 'Staged operation in progress',
                -2147415735: 'Staged operation not started',
                -2147415779: 'Unsupported keyattr mask',
                -2147415781: 'Unsupported keyusage mask',
                -2147415785: 'Unsupported key format',
                -2147415777: 'Unsupported key label',
                -2147415784: 'Unsupported key size',
                -2147415839: 'User canceled',
                -2147415767: 'Vector of bufs unsupported',
                -2147415734: 'Verify failed',
            }
            if num in code_map:
                output = code_map[num]

        if not output:
            output = '%s %s' % (domain, num)

    raise OSError(output)


CFHelpers.register_native_mapping(
    CoreFoundation.CFStringGetTypeID(),
    CFHelpers.cf_string_to_unicode
)
CFHelpers.register_native_mapping(
    CoreFoundation.CFNumberGetTypeID(),
    CFHelpers.cf_number_to_number
)
CFHelpers.register_native_mapping(
    CoreFoundation.CFDataGetTypeID(),
    CFHelpers.cf_data_to_bytes
)
CFHelpers.register_native_mapping(
    CoreFoundation.CFDictionaryGetTypeID(),
    CFHelpers.cf_dictionary_to_dict
)
