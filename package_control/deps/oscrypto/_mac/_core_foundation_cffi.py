# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from .._ffi import (
    buffer_from_bytes,
    byte_string_from_buffer,
    deref,
    is_null,
    new,
    register_ffi,
)

from cffi import FFI


__all__ = [
    'CFHelpers',
    'CoreFoundation',
]


ffi = FFI()
ffi.cdef("""
    typedef bool Boolean;
    typedef long CFIndex;
    typedef unsigned long CFStringEncoding;
    typedef unsigned long CFNumberType;
    typedef unsigned long CFTypeID;

    typedef void *CFTypeRef;
    typedef CFTypeRef CFArrayRef;
    typedef CFTypeRef CFDataRef;
    typedef CFTypeRef CFStringRef;
    typedef CFTypeRef CFNumberRef;
    typedef CFTypeRef CFBooleanRef;
    typedef CFTypeRef CFDictionaryRef;
    typedef CFTypeRef CFErrorRef;
    typedef CFTypeRef CFAllocatorRef;

    typedef struct {
        CFIndex version;
        void *retain;
        void *release;
        void *copyDescription;
        void *equal;
        void *hash;
    } CFDictionaryKeyCallBacks;

    typedef struct {
        CFIndex version;
        void *retain;
        void *release;
        void *copyDescription;
        void *equal;
    } CFDictionaryValueCallBacks;

    typedef struct {
        CFIndex version;
        void *retain;
        void *release;
        void *copyDescription;
        void *equal;
    } CFArrayCallBacks;

    CFIndex CFDataGetLength(CFDataRef theData);
    const char *CFDataGetBytePtr(CFDataRef theData);
    CFDataRef CFDataCreate(CFAllocatorRef allocator, const char *bytes, CFIndex length);

    CFDictionaryRef CFDictionaryCreate(CFAllocatorRef allocator, const void **keys, const void **values,
                    CFIndex numValues, const CFDictionaryKeyCallBacks *keyCallBacks,
                    const CFDictionaryValueCallBacks *valueCallBacks);
    CFIndex CFDictionaryGetCount(CFDictionaryRef theDict);

    const char *CFStringGetCStringPtr(CFStringRef theString, CFStringEncoding encoding);
    Boolean CFStringGetCString(CFStringRef theString, char *buffer, CFIndex bufferSize, CFStringEncoding encoding);
    CFStringRef CFStringCreateWithCString(CFAllocatorRef alloc, const char *cStr, CFStringEncoding encoding);

    CFNumberRef CFNumberCreate(CFAllocatorRef allocator, CFNumberType theType, const void *valuePtr);

    CFStringRef CFCopyTypeIDDescription(CFTypeID type_id);

    void CFRelease(CFTypeRef cf);
    void CFRetain(CFTypeRef cf);

    CFStringRef CFErrorCopyDescription(CFErrorRef err);
    CFStringRef CFErrorGetDomain(CFErrorRef err);
    CFIndex CFErrorGetCode(CFErrorRef err);

    Boolean CFBooleanGetValue(CFBooleanRef boolean);

    CFTypeID CFDictionaryGetTypeID(void);
    CFTypeID CFNumberGetTypeID(void);
    CFTypeID CFStringGetTypeID(void);
    CFTypeID CFDataGetTypeID(void);

    CFArrayRef CFArrayCreate(CFAllocatorRef allocator, const void **values, CFIndex numValues,
                    const CFArrayCallBacks *callBacks);
    CFIndex CFArrayGetCount(CFArrayRef theArray);
    CFTypeRef CFArrayGetValueAtIndex(CFArrayRef theArray, CFIndex idx);
    CFNumberType CFNumberGetType(CFNumberRef number);
    Boolean CFNumberGetValue(CFNumberRef number, CFNumberType theType, void *valuePtr);
    CFIndex CFDictionaryGetKeysAndValues(CFDictionaryRef theDict, const void **keys, const void **values);
    CFTypeID CFGetTypeID(CFTypeRef cf);

    extern CFAllocatorRef kCFAllocatorDefault;
    extern CFArrayCallBacks kCFTypeArrayCallBacks;
    extern CFBooleanRef kCFBooleanTrue;
    extern CFDictionaryKeyCallBacks kCFTypeDictionaryKeyCallBacks;
    extern CFDictionaryValueCallBacks kCFTypeDictionaryValueCallBacks;
""")

core_foundation_path = '/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation'

CoreFoundation = ffi.dlopen(core_foundation_path)
register_ffi(CoreFoundation, ffi)

kCFNumberCFIndexType = 14
kCFStringEncodingUTF8 = 0x08000100


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

        type_ = CoreFoundation.CFNumberGetType(value)
        type_name_ = {
            1: 'int8_t',      # kCFNumberSInt8Type
            2: 'in16_t',      # kCFNumberSInt16Type
            3: 'int32_t',     # kCFNumberSInt32Type
            4: 'int64_t',     # kCFNumberSInt64Type
            5: 'float',       # kCFNumberFloat32Type
            6: 'double',      # kCFNumberFloat64Type
            7: 'char',        # kCFNumberCharType
            8: 'short',       # kCFNumberShortType
            9: 'int',         # kCFNumberIntType
            10: 'long',       # kCFNumberLongType
            11: 'long long',  # kCFNumberLongLongType
            12: 'float',      # kCFNumberFloatType
            13: 'double',     # kCFNumberDoubleType
            14: 'long',       # kCFNumberCFIndexType
            15: 'int',        # kCFNumberNSIntegerType
            16: 'double',     # kCFNumberCGFloatType
        }[type_]
        output = new(CoreFoundation, type_name_ + ' *')
        CoreFoundation.CFNumberGetValue(value, type_, output)
        return deref(output)

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

        keys = new(CoreFoundation, 'CFTypeRef[%s]' % dict_length)
        values = new(CoreFoundation, 'CFTypeRef[%s]' % dict_length)
        CoreFoundation.CFDictionaryGetKeysAndValues(
            dictionary,
            keys,
            values
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

        string_ptr = CoreFoundation.CFStringGetCStringPtr(
            value,
            kCFStringEncodingUTF8
        )
        string = None if is_null(string_ptr) else ffi.string(string_ptr)
        if string is None:
            buffer = buffer_from_bytes(1024)
            result = CoreFoundation.CFStringGetCString(
                value,
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
        return ffi.buffer(start, num_bytes)[:]

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
        return CoreFoundation.CFDictionaryCreate(
            CoreFoundation.kCFAllocatorDefault,
            keys,
            values,
            length,
            ffi.addressof(CoreFoundation.kCFTypeDictionaryKeyCallBacks),
            ffi.addressof(CoreFoundation.kCFTypeDictionaryValueCallBacks)
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
        return CoreFoundation.CFArrayCreate(
            CoreFoundation.kCFAllocatorDefault,
            values,
            length,
            ffi.addressof(CoreFoundation.kCFTypeArrayCallBacks)
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

        integer_as_long = ffi.new('long *', integer)
        return CoreFoundation.CFNumberCreate(
            CoreFoundation.kCFAllocatorDefault,
            kCFNumberCFIndexType,
            integer_as_long
        )
