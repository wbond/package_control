# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from ctypes import c_void_p, c_long, c_uint32, c_char_p, c_byte, c_ulong, c_bool
from ctypes import CDLL, string_at, cast, POINTER, byref
import ctypes

from .._ffi import FFIEngineError, buffer_from_bytes, byte_string_from_buffer


__all__ = [
    'CFHelpers',
    'CoreFoundation',
]


core_foundation_path = '/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation'

CoreFoundation = CDLL(core_foundation_path, use_errno=True)

CFIndex = c_long
CFStringEncoding = c_uint32
CFArray = c_void_p
CFData = c_void_p
CFString = c_void_p
CFNumber = c_void_p
CFDictionary = c_void_p
CFError = c_void_p
CFType = c_void_p
CFTypeID = c_ulong
CFBoolean = c_void_p
CFNumberType = c_uint32

CFTypeRef = POINTER(CFType)
CFArrayRef = POINTER(CFArray)
CFDataRef = POINTER(CFData)
CFStringRef = POINTER(CFString)
CFNumberRef = POINTER(CFNumber)
CFBooleanRef = POINTER(CFBoolean)
CFDictionaryRef = POINTER(CFDictionary)
CFErrorRef = POINTER(CFError)
CFAllocatorRef = c_void_p
CFDictionaryKeyCallBacks = c_void_p
CFDictionaryValueCallBacks = c_void_p
CFArrayCallBacks = c_void_p

pointer_p = POINTER(c_void_p)

try:
    CoreFoundation.CFDataGetLength.argtypes = [
        CFDataRef
    ]
    CoreFoundation.CFDataGetLength.restype = CFIndex

    CoreFoundation.CFDataGetBytePtr.argtypes = [
        CFDataRef
    ]
    CoreFoundation.CFDataGetBytePtr.restype = c_void_p

    CoreFoundation.CFDataCreate.argtypes = [
        CFAllocatorRef,
        c_char_p,
        CFIndex
    ]
    CoreFoundation.CFDataCreate.restype = CFDataRef

    CoreFoundation.CFDictionaryCreate.argtypes = [
        CFAllocatorRef,
        CFStringRef,
        CFTypeRef,
        CFIndex,
        CFDictionaryKeyCallBacks,
        CFDictionaryValueCallBacks
    ]
    CoreFoundation.CFDictionaryCreate.restype = CFDictionaryRef

    CoreFoundation.CFDictionaryGetCount.argtypes = [
        CFDictionaryRef
    ]
    CoreFoundation.CFDictionaryGetCount.restype = CFIndex

    CoreFoundation.CFStringGetCStringPtr.argtypes = [
        CFStringRef,
        CFStringEncoding
    ]
    CoreFoundation.CFStringGetCStringPtr.restype = c_char_p

    CoreFoundation.CFStringGetCString.argtypes = [
        CFStringRef,
        c_char_p,
        CFIndex,
        CFStringEncoding
    ]
    CoreFoundation.CFStringGetCString.restype = c_bool

    CoreFoundation.CFStringCreateWithCString.argtypes = [
        CFAllocatorRef,
        c_char_p,
        CFStringEncoding
    ]
    CoreFoundation.CFStringCreateWithCString.restype = CFStringRef

    CoreFoundation.CFNumberCreate.argtypes = [
        CFAllocatorRef,
        CFNumberType,
        c_void_p
    ]
    CoreFoundation.CFNumberCreate.restype = CFNumberRef

    CoreFoundation.CFCopyTypeIDDescription.argtypes = [
        CFTypeID
    ]
    CoreFoundation.CFCopyTypeIDDescription.restype = CFStringRef

    CoreFoundation.CFRelease.argtypes = [
        CFTypeRef
    ]
    CoreFoundation.CFRelease.restype = None

    CoreFoundation.CFRetain.argtypes = [
        CFTypeRef
    ]
    CoreFoundation.CFRetain.restype = None

    CoreFoundation.CFErrorCopyDescription.argtypes = [
        CFErrorRef
    ]
    CoreFoundation.CFErrorCopyDescription.restype = CFStringRef

    CoreFoundation.CFErrorGetDomain.argtypes = [
        CFErrorRef
    ]
    CoreFoundation.CFErrorGetDomain.restype = CFStringRef

    CoreFoundation.CFErrorGetCode.argtypes = [
        CFErrorRef
    ]
    CoreFoundation.CFErrorGetCode.restype = CFIndex

    CoreFoundation.CFBooleanGetValue.argtypes = [
        CFBooleanRef
    ]
    CoreFoundation.CFBooleanGetValue.restype = c_byte

    CoreFoundation.CFDictionaryGetTypeID.argtypes = []
    CoreFoundation.CFDictionaryGetTypeID.restype = CFTypeID

    CoreFoundation.CFNumberGetTypeID.argtypes = []
    CoreFoundation.CFNumberGetTypeID.restype = CFTypeID

    CoreFoundation.CFStringGetTypeID.argtypes = []
    CoreFoundation.CFStringGetTypeID.restype = CFTypeID

    CoreFoundation.CFDataGetTypeID.argtypes = []
    CoreFoundation.CFDataGetTypeID.restype = CFTypeID

    CoreFoundation.CFArrayCreate.argtypes = [
        CFAllocatorRef,
        POINTER(c_void_p),
        CFIndex,
        CFArrayCallBacks
    ]
    CoreFoundation.CFArrayCreate.restype = CFArrayRef

    CoreFoundation.CFArrayGetCount.argtypes = [
        CFArrayRef
    ]
    CoreFoundation.CFArrayGetCount.restype = CFIndex

    CoreFoundation.CFArrayGetValueAtIndex.argtypes = [
        CFArrayRef,
        CFIndex
    ]
    CoreFoundation.CFArrayGetValueAtIndex.restype = CFTypeRef

    CoreFoundation.CFNumberGetType.argtypes = [
        CFNumberRef
    ]
    CoreFoundation.CFNumberGetType.restype = CFNumberType

    CoreFoundation.CFNumberGetValue.argtypes = [
        CFNumberRef,
        CFNumberType,
        c_void_p
    ]
    CoreFoundation.CFNumberGetValue.restype = c_bool

    CoreFoundation.CFDictionaryGetKeysAndValues.argtypes = [
        CFDictionaryRef,
        pointer_p,
        pointer_p
    ]
    CoreFoundation.CFDictionaryGetKeysAndValues.restype = CFIndex

    CoreFoundation.CFGetTypeID.argtypes = [
        CFTypeRef
    ]
    CoreFoundation.CFGetTypeID.restype = CFTypeID

    setattr(CoreFoundation, 'kCFAllocatorDefault', CFAllocatorRef.in_dll(CoreFoundation, 'kCFAllocatorDefault'))
    setattr(CoreFoundation, 'kCFBooleanTrue', CFTypeRef.in_dll(CoreFoundation, 'kCFBooleanTrue'))

    kCFTypeDictionaryKeyCallBacks = c_void_p.in_dll(CoreFoundation, 'kCFTypeDictionaryKeyCallBacks')
    kCFTypeDictionaryValueCallBacks = c_void_p.in_dll(CoreFoundation, 'kCFTypeDictionaryValueCallBacks')
    kCFTypeArrayCallBacks = c_void_p.in_dll(CoreFoundation, 'kCFTypeArrayCallBacks')

except (AttributeError):
    raise FFIEngineError('Error initializing ctypes')

setattr(CoreFoundation, 'CFDataRef', CFDataRef)
setattr(CoreFoundation, 'CFErrorRef', CFErrorRef)
setattr(CoreFoundation, 'CFArrayRef', CFArrayRef)
kCFNumberCFIndexType = CFNumberType(14)
kCFStringEncodingUTF8 = CFStringEncoding(0x08000100)


def _cast_pointer_p(value):
    """
    Casts a value to a pointer of a pointer

    :param value:
        A ctypes object

    :return:
        A POINTER(c_void_p) object
    """

    return cast(value, pointer_p)


class CFHelpers():
    """
    Namespace for core foundation helpers
    """

    _native_map = {}

    @classmethod
    def register_native_mapping(cls, type_id, callback):
        """
        Register a function to convert a core foundation data type into its
        equivalent in python

        :param type_id:
            The CFTypeId for the type

        :param callback:
            A callback to pass the CFType object to
        """

        cls._native_map[int(type_id)] = callback

    @staticmethod
    def cf_number_to_number(value):
        """
        Converts a CFNumber object to a python float or integer

        :param value:
            The CFNumber object

        :return:
            A python number (float or integer)
        """

        type_ = CoreFoundation.CFNumberGetType(_cast_pointer_p(value))
        c_type = {
            1: c_byte,              # kCFNumberSInt8Type
            2: ctypes.c_short,      # kCFNumberSInt16Type
            3: ctypes.c_int32,      # kCFNumberSInt32Type
            4: ctypes.c_int64,      # kCFNumberSInt64Type
            5: ctypes.c_float,      # kCFNumberFloat32Type
            6: ctypes.c_double,     # kCFNumberFloat64Type
            7: c_byte,              # kCFNumberCharType
            8: ctypes.c_short,      # kCFNumberShortType
            9: ctypes.c_int,        # kCFNumberIntType
            10: c_long,             # kCFNumberLongType
            11: ctypes.c_longlong,  # kCFNumberLongLongType
            12: ctypes.c_float,     # kCFNumberFloatType
            13: ctypes.c_double,    # kCFNumberDoubleType
            14: c_long,             # kCFNumberCFIndexType
            15: ctypes.c_int,       # kCFNumberNSIntegerType
            16: ctypes.c_double,    # kCFNumberCGFloatType
        }[type_]
        output = c_type(0)
        CoreFoundation.CFNumberGetValue(_cast_pointer_p(value), type_, byref(output))
        return output.value

    @staticmethod
    def cf_dictionary_to_dict(dictionary):
        """
        Converts a CFDictionary object into a python dictionary

        :param dictionary:
            The CFDictionary to convert

        :return:
            A python dict
        """

        dict_length = CoreFoundation.CFDictionaryGetCount(dictionary)

        keys = (CFTypeRef * dict_length)()
        values = (CFTypeRef * dict_length)()
        CoreFoundation.CFDictionaryGetKeysAndValues(
            dictionary,
            _cast_pointer_p(keys),
            _cast_pointer_p(values)
        )

        output = {}
        for index in range(0, dict_length):
            output[CFHelpers.native(keys[index])] = CFHelpers.native(values[index])

        return output

    @classmethod
    def native(cls, value):
        """
        Converts a CF* object into its python equivalent

        :param value:
            The CF* object to convert

        :return:
            The native python object
        """

        type_id = CoreFoundation.CFGetTypeID(value)
        if type_id in cls._native_map:
            return cls._native_map[type_id](value)
        else:
            return value

    @staticmethod
    def cf_string_to_unicode(value):
        """
        Creates a python unicode string from a CFString object

        :param value:
            The CFString to convert

        :return:
            A python unicode string
        """

        string = CoreFoundation.CFStringGetCStringPtr(
            _cast_pointer_p(value),
            kCFStringEncodingUTF8
        )
        if string is None:
            buffer = buffer_from_bytes(1024)
            result = CoreFoundation.CFStringGetCString(
                _cast_pointer_p(value),
                buffer,
                1024,
                kCFStringEncodingUTF8
            )
            if not result:
                raise OSError('Error copying C string from CFStringRef')
            string = byte_string_from_buffer(buffer)
        if string is not None:
            string = string.decode('utf-8')
        return string

    @staticmethod
    def cf_string_from_unicode(string):
        """
        Creates a CFStringRef object from a unicode string

        :param string:
            The unicode string to create the CFString object from

        :return:
            A CFStringRef
        """

        return CoreFoundation.CFStringCreateWithCString(
            CoreFoundation.kCFAllocatorDefault,
            string.encode('utf-8'),
            kCFStringEncodingUTF8
        )

    @staticmethod
    def cf_data_to_bytes(value):
        """
        Extracts a bytestring from a CFData object

        :param value:
            A CFData object

        :return:
            A byte string
        """

        start = CoreFoundation.CFDataGetBytePtr(value)
        num_bytes = CoreFoundation.CFDataGetLength(value)
        return string_at(start, num_bytes)

    @staticmethod
    def cf_data_from_bytes(bytes_):
        """
        Creates a CFDataRef object from a byte string

        :param bytes_:
            The data to create the CFData object from

        :return:
            A CFDataRef
        """

        return CoreFoundation.CFDataCreate(
            CoreFoundation.kCFAllocatorDefault,
            bytes_,
            len(bytes_)
        )

    @staticmethod
    def cf_dictionary_from_pairs(pairs):
        """
        Creates a CFDictionaryRef object from a list of 2-element tuples
        representing the key and value. Each key should be a CFStringRef and each
        value some sort of CF* type.

        :param pairs:
            A list of 2-element tuples

        :return:
            A CFDictionaryRef
        """

        length = len(pairs)
        keys = []
        values = []
        for pair in pairs:
            key, value = pair
            keys.append(key)
            values.append(value)
        keys = (CFStringRef * length)(*keys)
        values = (CFTypeRef * length)(*values)
        return CoreFoundation.CFDictionaryCreate(
            CoreFoundation.kCFAllocatorDefault,
            _cast_pointer_p(byref(keys)),
            _cast_pointer_p(byref(values)),
            length,
            kCFTypeDictionaryKeyCallBacks,
            kCFTypeDictionaryValueCallBacks
        )

    @staticmethod
    def cf_array_from_list(values):
        """
        Creates a CFArrayRef object from a list of CF* type objects.

        :param values:
            A list of CF* type object

        :return:
            A CFArrayRef
        """

        length = len(values)
        values = (CFTypeRef * length)(*values)
        return CoreFoundation.CFArrayCreate(
            CoreFoundation.kCFAllocatorDefault,
            _cast_pointer_p(byref(values)),
            length,
            kCFTypeArrayCallBacks
        )

    @staticmethod
    def cf_number_from_integer(integer):
        """
        Creates a CFNumber object from an integer

        :param integer:
            The integer to create the CFNumber for

        :return:
            A CFNumber
        """

        integer_as_long = c_long(integer)
        return CoreFoundation.CFNumberCreate(
            CoreFoundation.kCFAllocatorDefault,
            kCFNumberCFIndexType,
            byref(integer_as_long)
        )
