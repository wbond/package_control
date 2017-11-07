# coding: utf-8

"""
Exceptions and compatibility shims for consistently using ctypes and cffi
"""

from __future__ import unicode_literals, division, absolute_import, print_function

import sys
from ._types import str_cls, byte_cls, int_types, bytes_to_list


__all__ = [
    'array_from_pointer',
    'array_set',
    'buffer_from_bytes',
    'buffer_from_unicode',
    'buffer_pointer',
    'byte_array',
    'byte_string_from_buffer',
    'bytes_from_buffer',
    'callback',
    'cast',
    'deref',
    'errno',
    'FFIEngineError',
    'is_null',
    'native',
    'new',
    'null',
    'pointer_set',
    'ref',
    'register_ffi',
    'sizeof',
    'struct',
    'struct_bytes',
    'struct_from_buffer',
    'unwrap',
    'write_to_buffer',
]


try:
    from cffi import FFI

    _ffi_registry = {}

    ffi = FFI()

    def register_ffi(library, ffi_obj):
        _ffi_registry[library] = ffi_obj

    def _get_ffi(library):
        if library in _ffi_registry:
            return _ffi_registry[library]
        return ffi

    def buffer_from_bytes(initializer):
        if sys.platform == 'win32':
            return ffi.new('unsigned char[]', initializer)
        return ffi.new('char[]', initializer)

    def buffer_from_unicode(initializer):
        return ffi.new('wchar_t []', initializer)

    def write_to_buffer(buffer, data, offset=0):
        buffer[offset:offset + len(data)] = data

    def buffer_pointer(buffer):
        return ffi.new('char *[]', [buffer])

    def cast(library, type_, value):
        ffi_obj = _get_ffi(library)
        return ffi_obj.cast(type_, value)

    def sizeof(library, value):
        ffi_obj = _get_ffi(library)
        return ffi_obj.sizeof(value)

    def bytes_from_buffer(buffer, maxlen=None):
        if maxlen is not None:
            return ffi.buffer(buffer, maxlen)[:]
        return ffi.buffer(buffer)[:]

    def byte_string_from_buffer(buffer):
        return ffi.string(buffer)

    def byte_array(byte_string):
        return byte_string

    def pointer_set(pointer_, value):
        pointer_[0] = value

    def array_set(array, value):
        for index, val in enumerate(value):
            array[index] = val

    def null():
        return ffi.NULL

    def is_null(point):
        if point is None:
            return True
        if point == ffi.NULL:
            return True
        if ffi.getctype(ffi.typeof(point)) == 'void *':
            return False
        if point[0] == ffi.NULL:
            return True
        return False

    def errno():
        return ffi.errno

    def new(library, type_, value=None):
        ffi_obj = _get_ffi(library)

        params = []
        if value is not None:
            params.append(value)
        if type_ in set(['BCRYPT_KEY_HANDLE', 'BCRYPT_ALG_HANDLE']):
            return ffi_obj.cast(type_, 0)
        return ffi_obj.new(type_, *params)

    def ref(value, offset=0):
        return value + offset

    def native(type_, value):
        if type_ == str_cls:
            return ffi.string(value)
        if type_ == byte_cls:
            return ffi.buffer(value)[:]
        return type_(value)

    def deref(point):
        return point[0]

    def unwrap(point):
        return point[0]

    def struct(library, name):
        ffi_obj = _get_ffi(library)
        return ffi_obj.new('%s *' % name)

    def struct_bytes(struct_):
        return ffi.buffer(struct_)[:]

    def struct_from_buffer(library, name, buffer):
        ffi_obj = _get_ffi(library)
        new_struct_pointer = ffi_obj.new('%s *' % name)
        new_struct = new_struct_pointer[0]
        struct_size = sizeof(library, new_struct)
        struct_buffer = ffi_obj.buffer(new_struct_pointer)
        struct_buffer[:] = ffi_obj.buffer(buffer, struct_size)[:]
        return new_struct_pointer

    def array_from_pointer(library, name, point, size):
        ffi_obj = _get_ffi(library)
        array = ffi_obj.cast('%s[%s]' % (name, size), point)
        total_bytes = ffi_obj.sizeof(array)
        if total_bytes == 0:
            return []
        output = []

        string_types = {
            'LPSTR': True,
            'LPCSTR': True,
            'LPWSTR': True,
            'LPCWSTR': True,
            'char *': True,
            'wchar_t *': True,
        }
        string_type = name in string_types

        for i in range(0, size):
            value = array[i]
            if string_type:
                value = ffi_obj.string(value)
            output.append(value)
        return output

    def callback(library, signature_name, func):
        ffi_obj = _get_ffi(library)
        return ffi_obj.callback(signature_name, func)

    engine = 'cffi'

except (ImportError):

    import ctypes
    from ctypes import pointer, c_int, c_char_p, c_uint, c_void_p, c_wchar_p

    _pointer_int_types = int_types + (c_char_p, ctypes.POINTER(ctypes.c_byte))

    _pointer_types = {
        'void *': True,
        'wchar_t *': True,
        'char *': True,
        'char **': True,
    }
    _type_map = {
        'void *': c_void_p,
        'wchar_t *': c_wchar_p,
        'char *': c_char_p,
        'char **': ctypes.POINTER(c_char_p),
        'int': c_int,
        'unsigned int': c_uint,
        'size_t': ctypes.c_size_t,
        'uint32_t': ctypes.c_uint32,
    }
    if sys.platform == 'win32':
        from ctypes import wintypes
        _pointer_types.update({
            'LPSTR': True,
            'LPWSTR': True,
            'LPCSTR': True,
            'LPCWSTR': True,
        })
        _type_map.update({
            'BYTE': ctypes.c_byte,
            'LPSTR': c_char_p,
            'LPWSTR': c_wchar_p,
            'LPCSTR': c_char_p,
            'LPCWSTR': c_wchar_p,
            'ULONG': wintypes.ULONG,
            'DWORD': wintypes.DWORD,
            'char *': ctypes.POINTER(ctypes.c_byte),
            'char **': ctypes.POINTER(ctypes.POINTER(ctypes.c_byte)),
        })

    def _type_info(library, type_):
        is_double_pointer = type_[-3:] == ' **'
        if is_double_pointer:
            type_ = type_[:-1]
        is_pointer = type_[-2:] == ' *' and type_ not in _pointer_types
        if is_pointer:
            type_ = type_[:-2]

        is_array = type_.find('[') != -1
        if is_array:
            is_array = type_[type_.find('[') + 1:type_.find(']')]
            if is_array == '':
                is_array = True
            else:
                is_array = int(is_array)
            type_ = type_[0:type_.find('[')]

        if type_ in _type_map:
            type_ = _type_map[type_]
        else:
            type_ = getattr(library, type_)

        if is_double_pointer:
            type_ = ctypes.POINTER(type_)

        return (is_pointer, is_array, type_)

    def register_ffi(library, ffi_obj):
        pass

    def buffer_from_bytes(initializer):
        return ctypes.create_string_buffer(initializer)

    def buffer_from_unicode(initializer):
        return ctypes.create_unicode_buffer(initializer)

    def write_to_buffer(buffer, data, offset=0):
        if isinstance(buffer, ctypes.POINTER(ctypes.c_byte)):
            ctypes.memmove(buffer, data, len(data))
            return

        if offset == 0:
            buffer.value = data
        else:
            buffer.value = buffer.raw[0:offset] + data

    def buffer_pointer(buffer):
        return pointer(ctypes.cast(buffer, c_char_p))

    def cast(library, type_, value):
        is_pointer, is_array, type_ = _type_info(library, type_)

        if is_pointer:
            type_ = ctypes.POINTER(type_)
        elif is_array:
            type_ = type_ * is_array

        return ctypes.cast(value, type_)

    def sizeof(library, value):
        return ctypes.sizeof(value)

    def bytes_from_buffer(buffer, maxlen=None):
        if isinstance(buffer, _pointer_int_types):
            return ctypes.string_at(buffer, maxlen)
        if maxlen is not None:
            return buffer.raw[0:maxlen]
        return buffer.raw

    def byte_string_from_buffer(buffer):
        return buffer.value

    def byte_array(byte_string):
        return (ctypes.c_byte * len(byte_string))(*bytes_to_list(byte_string))

    def pointer_set(pointer_, value):
        pointer_.contents.value = value

    def array_set(array, value):
        for index, val in enumerate(value):
            array[index] = val

    def null():
        return None

    def is_null(point):
        return not bool(point)

    def errno():
        return ctypes.get_errno()

    def new(library, type_, value=None):
        is_pointer, is_array, type_ = _type_info(library, type_)
        if is_array:
            if is_array is True:
                type_ = type_ * value
                value = None
            else:
                type_ = type_ * is_array

        params = []
        if value is not None:
            params.append(value)
        output = type_(*params)

        if is_pointer:
            output = pointer(output)

        return output

    def ref(value, offset=0):
        return ctypes.cast(ctypes.addressof(value) + offset, ctypes.POINTER(ctypes.c_byte))

    def native(type_, value):
        if isinstance(value, type_):
            return value
        if sys.version_info < (3,) and type_ == int and isinstance(value, int_types):
            return value
        if isinstance(value, ctypes.Array) and value._type_ == ctypes.c_byte:
            return ctypes.string_at(ctypes.addressof(value), value._length_)
        return type_(value.value)

    def deref(point):
        return point[0]

    def unwrap(point):
        return point.contents

    def struct(library, name):
        return pointer(getattr(library, name)())

    def struct_bytes(struct_):
        return ctypes.string_at(struct_, ctypes.sizeof(struct_.contents))

    def struct_from_buffer(library, type_, buffer):
        class_ = getattr(library, type_)
        value = class_()
        ctypes.memmove(ctypes.addressof(value), buffer, ctypes.sizeof(class_))
        return ctypes.pointer(value)

    def array_from_pointer(library, type_, point, size):
        _, _, type_ = _type_info(library, type_)
        array = ctypes.cast(point, ctypes.POINTER(type_))
        output = []
        for i in range(0, size):
            output.append(array[i])
        return output

    def callback(library, signature_type, func):
        return getattr(library, signature_type)(func)

    engine = 'ctypes'


class FFIEngineError(Exception):

    """
    An exception when trying to instantiate ctypes or cffi
    """

    pass
