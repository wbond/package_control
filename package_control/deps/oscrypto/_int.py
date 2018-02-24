# coding: utf-8

"""
Function to fill ensure integers converted to a byte string are a specific
width. Exports the following items:

 - fill_width()
"""

from __future__ import unicode_literals, division, absolute_import, print_function


__all__ = [
    'fill_width',
]


def fill_width(bytes_, width):
    """
    Ensure a byte string representing a positive integer is a specific width
    (in bytes)

    :param bytes_:
        The integer byte string

    :param width:
        The desired width as an integer

    :return:
        A byte string of the width specified
    """

    while len(bytes_) < width:
        bytes_ = b'\x00' + bytes_
    return bytes_
