# coding: utf-8

"""
Miscellaneous data helpers, including functions for converting integers to and
from bytes and UTC timezone. Exports the following items:

 - OrderedDict()
 - int_from_bytes()
 - int_to_bytes()
 - timezone.utc
 - inet_ntop()
 - inet_pton()
 - uri_to_iri()
 - iri_to_uri()
"""

from __future__ import unicode_literals, division, absolute_import, print_function

import math
import sys

from ._iri import iri_to_uri, uri_to_iri  # noqa
from ._ordereddict import OrderedDict  # noqa

if sys.platform == 'win32':
    from ._inet import inet_ntop, inet_pton
else:
    from socket import inet_ntop, inet_pton  # noqa


# Python 2
if sys.version_info <= (3,):

    from datetime import timedelta, tzinfo

    def int_to_bytes(value, signed=False, width=None):
        """
        Converts an integer to a byte string

        :param value:
            The integer to convert

        :param signed:
            If the byte string should be encoded using two's complement

        :param width:
            None == auto, otherwise an integer of the byte width for the return
            value

        :return:
            A byte string
        """

        # Handle negatives in two's complement
        is_neg = False
        if signed and value < 0:
            is_neg = True
            bits = int(math.ceil(len('%x' % abs(value)) / 2.0) * 8)
            value = (value + (1 << bits)) % (1 << bits)

        hex_str = '%x' % value
        if len(hex_str) & 1:
            hex_str = '0' + hex_str

        output = hex_str.decode('hex')

        if signed and not is_neg and ord(output[0:1]) & 0x80:
            output = b'\x00' + output

        if width is not None:
            if is_neg:
                pad_char = b'\xFF'
            else:
                pad_char = b'\x00'
            output = (pad_char * (width - len(output))) + output
        elif is_neg and ord(output[0:1]) & 0x80 == 0:
            output = b'\xFF' + output

        return output

    def int_from_bytes(value, signed=False):
        """
        Converts a byte string to an integer

        :param value:
            The byte string to convert

        :param signed:
            If the byte string should be interpreted using two's complement

        :return:
            An integer
        """

        if value == b'':
            return 0

        num = long(value.encode("hex"), 16)  # noqa

        if not signed:
            return num

        # Check for sign bit and handle two's complement
        if ord(value[0:1]) & 0x80:
            bit_len = len(value) * 8
            return num - (1 << bit_len)

        return num

    class utc(tzinfo):  # noqa

        def tzname(self, _):
            return 'UTC+00:00'

        def utcoffset(self, _):
            return timedelta(0)

        def dst(self, _):
            return timedelta(0)

    class timezone():  # noqa

        utc = utc()


# Python 3
else:

    from datetime import timezone  # noqa

    def int_to_bytes(value, signed=False, width=None):
        """
        Converts an integer to a byte string

        :param value:
            The integer to convert

        :param signed:
            If the byte string should be encoded using two's complement

        :param width:
            None == auto, otherwise an integer of the byte width for the return
            value

        :return:
            A byte string
        """

        if width is None:
            width_ = math.ceil(value.bit_length() / 8) or 1
            try:
                return value.to_bytes(width_, byteorder='big', signed=signed)
            except (OverflowError):
                return value.to_bytes(width_ + 1, byteorder='big', signed=signed)
        else:
            return value.to_bytes(width, byteorder='big', signed=signed)

    def int_from_bytes(value, signed=False):
        """
        Converts a byte string to an integer

        :param value:
            The byte string to convert

        :param signed:
            If the byte string should be interpreted using two's complement

        :return:
            An integer
        """

        return int.from_bytes(value, 'big', signed=signed)
