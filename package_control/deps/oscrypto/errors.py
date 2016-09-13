# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import sys
import socket


__all__ = [
    'AsymmetricKeyError',
    'CACertsError',
    'LibraryNotFoundError',
    'SignatureError',
    'TLSError',
    'TLSVerificationError',
]


class LibraryNotFoundError(Exception):

    """
    An exception when trying to find a shared library
    """

    pass


class SignatureError(Exception):

    """
    An exception when validating a signature
    """

    pass


class AsymmetricKeyError(Exception):

    """
    An exception when a key is invalid or unsupported
    """

    pass


class IncompleteAsymmetricKeyError(AsymmetricKeyError):

    """
    An exception when a key is missing necessary information
    """

    pass


class CACertsError(Exception):

    """
    An exception when exporting CA certs from the OS trust store
    """

    pass


class TLSError(socket.error):

    """
    An exception related to TLS functionality
    """

    message = None

    def __init__(self, message):
        self.args = (message,)
        self.message = message

    def __str__(self):
        output = self.__unicode__()
        if sys.version_info < (3,):
            output = output.encode('utf-8')
        return output

    def __unicode__(self):
        return self.message


class TLSVerificationError(TLSError):

    """
    A server certificate verification error happened during a TLS handshake
    """

    certificate = None

    def __init__(self, message, certificate):
        TLSError.__init__(self, message)
        self.certificate = certificate
        self.args = (message, certificate)
