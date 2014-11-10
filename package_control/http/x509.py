import re
import sys
import datetime

if sys.version_info >= (3,):
    long = int
    str_cls = str
    bytes_cls = bytes
else:
    str_cls = unicode
    bytes_cls = str



Boolean = 0x01
Integer = 0x02
BitString = 0x03
OctetString = 0x04
Null = 0x05
ObjectIdentifier = 0x06
Enumerated = 0x0a
UTF8String = 0x0c
Sequence = 0x10
Set = 0x11
NumericString = 0x12
PrintableString = 0x13
T61String = 0x14
IA5String = 0x16
UTCTime = 0x17
GeneralizedTime = 0x18
VisibleString = 0x1a
UniversalString = 0x1c
BMPString = 0x1e

TypeConstructed = 0x20
TypePrimitive = 0x00

ClassUniversal = 0x00
ClassApplication = 0x40
ClassContext = 0x80
ClassPrivate = 0xc0


STRING_TYPES = [
    OctetString,
    IA5String,
    T61String,
    PrintableString,
    UTF8String,
    NumericString,
    VisibleString,
    UniversalString,
    BMPString
]


class Error(Exception):
    """ASN1 error"""


class Decoder(object):
    """A ASN.1 decoder. Understands BER (and DER which is a subset)."""

    def __init__(self):
        """Constructor."""
        self.m_stack = None
        self.m_tag = None

    def start(self, data):
        """Start processing `data'."""
        if not isinstance(data, bytes_cls):
            raise Error('Expecting string instance.')
        self.m_stack = [[0, data]]
        self.m_tag = None

    def peek(self):
        """Return the value of the next tag without moving to the next
        TLV record."""
        if self.m_stack is None:
            raise Error('No input selected. Call start() first.')
        if self._end_of_input():
            return None
        if self.m_tag is None:
            self.m_tag = self._read_tag()
        return self.m_tag

    def read(self):
        """Read a simple value and move to the next TLV record."""
        if self.m_stack is None:
            raise Error('No input selected. Call start() first.')
        if self._end_of_input():
            return None
        tag = self.peek()
        length = self._read_length()
        value = self._read_value(tag[0], length)
        self.m_tag = None
        return (tag, value)

    def eof(self):
        """Return True if we are end of input."""
        return self._end_of_input()

    def enter(self):
        """Enter a constructed tag."""
        if self.m_stack is None:
            raise Error('No input selected. Call start() first.')
        nr, typ, cls = self.peek()
        if typ != TypeConstructed:
            raise Error('Cannot enter a non-constructed tag.')
        length = self._read_length()
        bytes = self._read_bytes(length)
        self.m_stack.append([0, bytes])
        self.m_tag = None

    def leave(self):
        """Leave the last entered constructed tag."""
        if self.m_stack is None:
            raise Error('No input selected. Call start() first.')
        if len(self.m_stack) == 1:
            raise Error('Tag stack is empty.')
        del self.m_stack[-1]
        self.m_tag = None

    def _decode_boolean(self, bytes):
        """Decode a boolean value."""
        if len(bytes) != 1:
            raise Error('ASN1 syntax error')
        if bytes[0] == '\x00':
            return False
        return True

    def _read_tag(self):
        """Read a tag from the input."""
        byte = self._read_byte()
        cls = byte & 0xc0
        typ = byte & 0x20
        nr = byte & 0x1f
        if nr == 0x1f:
            nr = 0
            while True:
                byte = self._read_byte()
                nr = (nr << 7) | (byte & 0x7f)
                if not byte & 0x80:
                    break
        return (nr, typ, cls)

    def _read_length(self):
        """Read a length from the input."""
        byte = self._read_byte()
        if byte & 0x80:
            count = byte & 0x7f
            if count == 0x7f:
                raise Error('ASN1 syntax error')
            bytes = self._read_bytes(count)
            if sys.version_info < (3,):
                bytes = [ ord(b) for b in bytes ]
            length = long(0)
            for byte in bytes:
                length = (length << 8) | byte
            try:
                length = int(length)
            except OverflowError:
                pass
        else:
            length = byte
        return length

    def _read_value(self, nr, length):
        """Read a value from the input."""
        bytes = self._read_bytes(length)
        if nr == Boolean:
            value = self._decode_boolean(bytes)
        elif nr in (Integer, Enumerated):
            value = self._decode_integer(bytes)
        elif nr == OctetString:
            value = self._decode_octet_string(bytes)
        elif nr == UTF8String:
            value = self._decode_utf8_string(bytes)
        elif nr == PrintableString or nr == VisibleString or nr == NumericString:
            value = self._decode_printable_string(bytes)
        elif nr == UniversalString:
            value = self._decode_universal_string(bytes)
        elif nr == BMPString:
            value = self._decode_bmp_string(bytes)
        elif nr == T61String:
            value = self._decode_t61_string(bytes)
        elif nr == IA5String:
            value = self._decode_ia5_string(bytes)
        elif nr == UTCTime:
            value = self._decode_utc_time(bytes)
        elif nr == GeneralizedTime:
            value = self._decode_generalized_time(bytes)
        elif nr == Null:
            value = self._decode_null(bytes)
        elif nr == ObjectIdentifier:
            value = self._decode_object_identifier(bytes)
        else:
            value = bytes
        return value

    def _read_byte(self):
        """Return the next input byte, or raise an error on end-of-input."""
        index, input = self.m_stack[-1]
        try:
            if sys.version_info >= (3,):
                byte = input[index]
            else:
                byte = ord(input[index])
        except (IndexError) as e:
            raise Error('Premature end of input.')
        self.m_stack[-1][0] += 1
        return byte

    def _read_bytes(self, count):
        """Return the next `count' bytes of input. Raise error on
        end-of-input."""
        index, input = self.m_stack[-1]
        bytes = input[index:index+count]
        if len(bytes) != count:
            raise Error('Premature end of input.')
        self.m_stack[-1][0] += count
        return bytes

    def _end_of_input(self):
        """Return True if we are at the end of input."""
        index, input = self.m_stack[-1]
        assert not index > len(input)
        return index == len(input)

    def _decode_integer(self, bytes):
        """Decode an integer value."""
        if sys.version_info >= (3,):
            values = bytes
        else:
            values = [ ord(b) for b in bytes ]
        # check if the integer is normalized
        if len(values) > 1 and \
                (values[0] == 0xff and values[1] & 0x80 or
                 values[0] == 0x00 and not (values[1] & 0x80)):
            raise Error('ASN1 syntax error')
        negative = values[0] & 0x80
        if negative:
            # make positive by taking two's complement
            for i in range(len(values)):
                values[i] = 0xff - values[i]
            for i in range(len(values)-1, -1, -1):
                values[i] += 1
                if values[i] <= 0xff:
                    break
                assert i > 0
                values[i] = 0x00
        value = long(0)
        for val in values:
            value = (value << 8) |  val
        if negative:
            value = -value
        try:
            value = int(value)
        except OverflowError:
            pass
        return value

    def _decode_octet_string(self, bytes):
        """Decode an octet string."""
        return bytes

    def _decode_null(self, bytes):
        """Decode a Null value."""
        if len(bytes) != 0:
            raise Error('ASN1 syntax error')
        return None

    def _decode_object_identifier(self, bytes):
        """Decode an object identifier."""
        result = []
        value = 0
        for i in range(len(bytes)):
            if sys.version_info >= (3,):
                byte = bytes[i]
            else:
                byte = ord(bytes[i])
            if value == 0 and byte == 0x80:
                raise Error('ASN1 syntax error')
            value = (value << 7) | (byte & 0x7f)
            if not byte & 0x80:
                result.append(value)
                value = 0
        if len(result) == 0 or result[0] > 1599:
            raise Error('ASN1 syntax error')
        result = [result[0] // 40, result[0] % 40] + result[1:]
        result = map(str, result)
        return '.'.join(result)

    def _decode_printable_string(self, bytes):
        return str_cls(bytes, 'latin1')

    def _decode_ia5_string(self, bytes):
        return str_cls(bytes, 'latin1')

    def _decode_utf8_string(self, bytes):
        return str_cls(bytes, 'utf-8')

    def _decode_bmp_string(self, bytes):
        return str_cls(bytes, 'utf-16be')

    def _decode_universal_string(self, bytes):
        return str_cls(bytes, 'utf-32be')

    def _decode_utc_time(self, bytes):
        date_time = bytes.decode('ascii')
        if len(date_time) == 13:
            format = '%y%m%d%H%M%SZ'
        elif len(date_time) == 12:
            format = '%y%m%d%H%M%S'
        elif len(date_time) == 11:
            format = '%y%m%d%H%MZ'
        elif len(date_time) == 10:
            format = '%y%m%d%H%M'
        return datetime.datetime.strptime(date_time, format)

    def _decode_generalized_time(self, bytes):
        date_time = bytes.decode('ascii')
        if len(date_time) == 23:
            format = '%Y%m%d%H%M%S.%f%z'
        elif len(date_time) == 19 and date_time[-1] == 'Z':
            format = '%Y%m%d%H%M%S.%fZ'
        elif len(date_time) == 19:
            format = '%Y%m%d%H%M%S%z'
        elif len(date_time) == 18:
            format = '%Y%m%d%H%M%S.%f'
        elif len(date_time) == 15:
            format = '%Y%m%d%H%M%SZ'
        elif len(date_time) == 14:
            format = '%Y%m%d%H%M%S'
        return datetime.datetime.strptime(date_time, format)

    def _decode_t61_string(self, bytes):
        char_map = {
            0:   u"\u0000", 1:   u"\u0001", 2:   u"\u0002", 3:   u"\u0003",
            4:   u"\u0004", 5:   u"\u0005", 6:   u"\u0006", 7:   u"\u0007",
            8:   u"\u0008", 9:   u"\u0009", 10:  u"\u000A", 11:  u"\u000B",
            12:  u"\u000C", 13:  u"\u000D", 14:  u"\u000E", 15:  u"\u000F",
            16:  u"\u0010", 17:  u"\u0011", 18:  u"\u0012", 19:  u"\u0013",
            20:  u"\u0014", 21:  u"\u0015", 22:  u"\u0016", 23:  u"\u0017",
            24:  u"\u0018", 25:  u"\u0019", 26:  u"\u001A", 27:  u"\u001B",
            28:  u"\u001C", 29:  u"\u001D", 30:  u"\u001E", 31:  u"\u001F",
            32:  u"\u0020", 33:  u"\u0021", 34:  u"\u0022", 35:  u"",
            36:  u"",       37:  u"\u0025", 38:  u"\u0026", 39:  u"\u0027",
            40:  u"\u0028", 41:  u"\u0029", 42:  u"\u002A", 43:  u"\u002B",
            44:  u"\u002C", 45:  u"\u002D", 46:  u"\u002E", 47:  u"\u002F",
            48:  u"\u0030", 49:  u"\u0031", 50:  u"\u0032", 51:  u"\u0033",
            52:  u"\u0034", 53:  u"\u0035", 54:  u"\u0036", 55:  u"\u0037",
            56:  u"\u0038", 57:  u"\u0039", 58:  u"\u003A", 59:  u"\u003B",
            60:  u"\u003C", 61:  u"\u003D", 62:  u"\u003E", 63:  u"\u003F",
            64:  u"\u0040", 65:  u"\u0041", 66:  u"\u0042", 67:  u"\u0043",
            68:  u"\u0044", 69:  u"\u0045", 70:  u"\u0046", 71:  u"\u0047",
            72:  u"\u0048", 73:  u"\u0049", 74:  u"\u004A", 75:  u"\u004B",
            76:  u"\u004C", 77:  u"\u004D", 78:  u"\u004E", 79:  u"\u004F",
            80:  u"\u0050", 81:  u"\u0051", 82:  u"\u0052", 83:  u"\u0053",
            84:  u"\u0054", 85:  u"\u0055", 86:  u"\u0056", 87:  u"\u0057",
            88:  u"\u0058", 89:  u"\u0059", 90:  u"\u005A", 91:  u"\u005B",
            92:  u"",       93:  u"\u005D", 94:  u"",       95:  u"\u005F",
            96:  u"",       97:  u"\u0061", 98:  u"\u0062", 99:  u"\u0063",
            100: u"\u0064", 101: u"\u0065", 102: u"\u0066", 103: u"\u0067",
            104: u"\u0068", 105: u"\u0069", 106: u"\u006A", 107: u"\u006B",
            108: u"\u006C", 109: u"\u006D", 110: u"\u006E", 111: u"\u006F",
            112: u"\u0070", 113: u"\u0071", 114: u"\u0072", 115: u"\u0073",
            116: u"\u0074", 117: u"\u0075", 118: u"\u0076", 119: u"\u0077",
            120: u"\u0078", 121: u"\u0079", 122: u"\u007A", 123: u"",
            124: u"\u007C", 125: u"",       126: u"",       127: u"\u007F",
            128: u"\u0080", 129: u"\u0081", 130: u"\u0082", 131: u"\u0083",
            132: u"\u0084", 133: u"\u0085", 134: u"\u0086", 135: u"\u0087",
            136: u"\u0088", 137: u"\u0089", 138: u"\u008A", 139: u"\u008B",
            140: u"\u008C", 141: u"\u008D", 142: u"\u008E", 143: u"\u008F",
            144: u"\u0090", 145: u"\u0091", 146: u"\u0092", 147: u"\u0093",
            148: u"\u0094", 149: u"\u0095", 150: u"\u0096", 151: u"\u0097",
            152: u"\u0098", 153: u"\u0099", 154: u"\u009A", 155: u"\u009B",
            156: u"\u009C", 157: u"\u009D", 158: u"\u009E", 159: u"\u009F",
            160: u"\u00A0", 161: u"\u00A1", 162: u"\u00A2", 163: u"\u00A3",
            164: u"\u0024", 165: u"\u00A5", 166: u"\u0023", 167: u"\u00A7",
            168: u"\u00A4", 169: u"",       170: u"",       171: u"\u00AB",
            172: u"",       173: u"",       174: u"",       175: u"",
            176: u"\u00B0", 177: u"\u00B1", 178: u"\u00B2", 179: u"\u00B3",
            180: u"\u00D7", 181: u"\u00B5", 182: u"\u00B6", 183: u"\u00B7",
            184: u"\u00F7", 185: u"",       186: u"",       187: u"\u00BB",
            188: u"\u00BC", 189: u"\u00BD", 190: u"\u00BE", 191: u"\u00BF",
            192: u"",       193: u"\u0300", 194: u"\u0301", 195: u"\u0302",
            196: u"\u0303", 197: u"\u0304", 198: u"\u0306", 199: u"\u0307",
            200: u"\u0308", 201: u"",       202: u"\u030A", 203: u"\u0327",
            204: u"\u0332", 205: u"\u030B", 206: u"\u0328", 207: u"\u030C",
            208: u"",       209: u"",       210: u"",       211: u"",
            212: u"",       213: u"",       214: u"",       215: u"",
            216: u"",       217: u"",       218: u"",       219: u"",
            220: u"",       221: u"",       222: u"",       223: u"",
            224: u"\u2126", 225: u"\u00C6", 226: u"\u00D0", 227: u"\u00AA",
            228: u"\u0126", 229: u"",       230: u"\u0132", 231: u"\u013F",
            232: u"\u0141", 233: u"\u00D8", 234: u"\u0152", 235: u"\u00BA",
            236: u"\u00DE", 237: u"\u0166", 238: u"\u014A", 239: u"\u0149",
            240: u"\u0138", 241: u"\u00E6", 242: u"\u0111", 243: u"\u00F0",
            244: u"\u0127", 245: u"\u0131", 246: u"\u0133", 247: u"\u0140",
            248: u"\u0142", 249: u"\u00F8", 250: u"\u0153", 251: u"\u00DF",
            252: u"\u00FE", 253: u"\u0167", 254: u"\u014B", 255: u""
        }
        output = u""
        for char in bytes:
            if sys.version_info < (3,):
                char = ord(char)
            output += char_map[char]
        return output


class SubjectAltNameDecoder(Decoder):
    def _read_value(self, nr, length):
        """Read a value from the input."""
        bytes = self._read_bytes(length)
        if nr in (1, 2, 6):
            value = self._decode_ia5_string(bytes)
        elif nr == 7:
            value = self._decode_octet_string(bytes)
        else:
            value = bytes
        return value


def load(data, decoder_cls=Decoder):
    """
    Parses an ASN1 stream into an AST

    :param input:
        A byte string or an instance of Decoder

    :return:
        An AST made up of a list of lists
    """

    if isinstance(data, bytes_cls):
        decoder = decoder_cls()
        decoder.start(data)
    else:
        decoder = data

    output = []

    while not decoder.eof():
        tag = decoder.peek()
        if tag[1] == TypePrimitive:
            tag, value = decoder.read()
            output.append([tag[0], value])

        elif tag[1] == TypeConstructed:
            decoder.enter()
            value = load(decoder)
            output.append([tag[0], value])
            decoder.leave()

    return output


def parse(data):
    """
    Takes the byte string of an x509 certificate and returns a dict
    containing the info in the cert

    :param data:
        The certificate byte string

    :return:
        A dict with the following keys:
         - version
    """

    structure = load(data)
    if structure[0][0] != Sequence:
        return None

    body = structure[0][1]
    if len(body) != 3:
        return None

    algo_oid_map = {
        '1.2.840.113549.1.1.1':  'rsaEncryption',
        '1.2.840.113549.1.1.2':  'md2WithRSAEncryption',
        '1.2.840.113549.1.1.4':  'md5WithRSAEncryption',
        '1.2.840.113549.1.1.5':  'sha1WithRSAEncryption',
        '1.2.840.113549.1.1.11': 'sha256WithRSAEncryption',
        '1.2.840.113549.1.1.12': 'sha384WithRSAEncryption',
        '1.2.840.113549.1.1.13': 'sha512WithRSAEncryption'
    }

    cert_struct = body[0][1]

    output = {}

    output['algorithm'] = body[1][1][0][1]
    if output['algorithm'] in algo_oid_map:
        output['algorithm'] = algo_oid_map[output['algorithm']]

    output['signature'] = body[2][1]

    i = 0

    # At least one CA cert on Windows was missing the version
    if cert_struct[i][0] == 0x00:
        output['version'] = cert_struct[i][1][0][1] + 1
        i += 1
    else:
        output['version'] = 3

    output['serialNumber'] = cert_struct[i][1]
    i += 1

    # The algorithm is repeated at cert_struct[i][1][0][1]
    i += 1

    output['issuer']    = parse_subject(cert_struct[i])
    i += 1

    output['notBefore'] = cert_struct[i][1][0][1]
    output['notAfter']  = cert_struct[i][1][1][1]
    i += 1

    output['subject']   = parse_subject(cert_struct[i])
    i += 1

    output['publicKeyAlgorithm'] = cert_struct[i][1][0][1][0][1]
    if output['publicKeyAlgorithm'] in algo_oid_map:
        output['publicKeyAlgorithm'] = algo_oid_map[output['publicKeyAlgorithm']]
    output['subjectPublicKey']   = cert_struct[i][1][1][1]
    i += 1

    for j in range(i, len(cert_struct)):
        if cert_struct[j][0] == 0x01:
            # Issuer unique identifier
            pass
        elif cert_struct[j][0] == 0x02:
            # Subject unique identifier
            pass
        elif cert_struct[j][0] == 0x03:
            output['subjectAltName'] = parse_subject_alt_name(cert_struct[j])

    return output


def parse_subject(data):
    """
    Takes the byte string or AST of an x509 subject and returns a dict

    :param data:
        The byte string or sub-section AST from load()

    :return:
        A dict contaning one or more of the following keys:
         - commonName
         - serialNumber
         - countryName
         - localityName
         - stateOrProvinceName
         - streetAddress
         - organizationName
         - organizationalUnitName
         - emailAddress
         - domainComponent
    """

    if isinstance(data, bytes_cls):
        structure = load(data)
    else:
        structure = [data]

    if structure[0][0] != Sequence:
        return None

    output = {}

    oid_map = {
        '2.5.4.3': 'commonName',
        '2.5.4.5': 'serialNumber',
        '2.5.4.6': 'countryName',
        '2.5.4.7': 'localityName',
        '2.5.4.8': 'stateOrProvinceName',
        '2.5.4.9': 'streetAddress',
        '2.5.4.10': 'organizationName',
        '2.5.4.11': 'organizationalUnitName',
        '1.2.840.113549.1.9.1': 'emailAddress',
        '0.9.2342.19200300.100.1.25': 'domainComponent'
    }

    body = structure[0][1]
    for part in body:
        if part[0] == Sequence:
            part = [Set, [part]]

        for subpart in part[1]:
            object_identifier = None
            value = None
            for element in subpart[1]:
                if element[0] == ObjectIdentifier:
                    object_identifier = element[1]
                elif element[0] in STRING_TYPES:
                    value = element[1]

            if object_identifier in oid_map:
                key = oid_map[object_identifier]
            else:
                key = object_identifier

            if key in output:
                if not isinstance(output[key], list):
                    output[key] = [output[key]]
                output[key].append(value)
            else:
                output[key] = value

    return output


def parse_subject_alt_name(ast):
    """
    Takes the byte string of an x509 certificate and returns a list
    of subject alt names

    :param ast:
        The AST of the x509 extensions part of the certificate structure

    :return:
        A tuple of unicode strings
    """

    extensions = {}
    for extension in ast[1][0][1]:
        object_identifier = None
        octet_string = None
        for part in extension[1]:
            if part[0] == OctetString:
                octet_string = part[1]
            elif part[0] == ObjectIdentifier:
                object_identifier = part[1]
        if object_identifier == '2.5.29.17':
            value = load(octet_string, SubjectAltNameDecoder)
        else:
            value = octet_string
        extensions[object_identifier] = value

    if not extensions or '2.5.29.17' not in extensions:
        return []

    values = extensions['2.5.29.17'][0][1]
    domains = []
    for value in values:
        if value[0] == 2:
            domains.append(('DNS', value[1]))

    return tuple(domains)
