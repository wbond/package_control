# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import os
import sys
import threading

from ._types import str_cls, type_name
from .errors import LibraryNotFoundError


__version__ = '0.17.1'
__version_info__ = (0, 17, 1)


_backend_lock = threading.Lock()
_module_values = {
    'backend': None,
    'backend_config': None
}


def backend():
    """
    :return:
        A unicode string of the backend being used: "openssl", "osx", "win"
    """

    if _module_values['backend'] is not None:
        return _module_values['backend']

    with _backend_lock:
        if _module_values['backend'] is not None:
            return _module_values['backend']

        if sys.platform == 'win32':
            _module_values['backend'] = 'win'
        elif sys.platform == 'darwin':
            _module_values['backend'] = 'osx'
        else:
            _module_values['backend'] = 'openssl'

        return _module_values['backend']


def _backend_config():
    """
    :return:
        A dict of config info for the backend. Only currently used by "openssl",
        it may contains zero or more of the following keys:
         - "libcrypto_path"
         - "libssl_path"
    """

    if backend() != 'openssl':
        return {}

    if _module_values['backend_config'] is not None:
        return _module_values['backend_config']

    with _backend_lock:
        if _module_values['backend_config'] is not None:
            return _module_values['backend_config']

        _module_values['backend_config'] = {}
        return _module_values['backend_config']


def use_openssl(libcrypto_path, libssl_path, trust_list_path=None):
    """
    Forces using OpenSSL dynamic libraries on OS X (.dylib) or Windows (.dll),
    or using a specific dynamic library on Linux/BSD (.so).

    This can also be used to configure oscrypto to use LibreSSL dynamic
    libraries.

    This method must be called before any oscrypto submodules are imported.

    :param libcrypto_path:
        A unicode string of the file path to the OpenSSL/LibreSSL libcrypto
        dynamic library.

    :param libssl_path:
        A unicode string of the file path to the OpenSSL/LibreSSL libssl
        dynamic library.

    :param trust_list_path:
        An optional unicode string of the path to a file containing
        OpenSSL-compatible CA certificates in PEM format. If this is not
        provided and the platform is OS X or Windows, the system trust roots
        will be exported from the OS and used for all TLS connections.

    :raises:
        ValueError - when one of the paths is not a unicode string
        OSError - when the trust_list_path does not exist on the filesystem
        oscrypto.errors.LibraryNotFoundError - when one of the path does not exist on the filesystem
        RuntimeError - when this function is called after another part of oscrypto has been imported
    """

    if not isinstance(libcrypto_path, str_cls):
        raise ValueError('libcrypto_path must be a unicode string, not %s' % type_name(libcrypto_path))

    if not isinstance(libssl_path, str_cls):
        raise ValueError('libssl_path must be a unicode string, not %s' % type_name(libssl_path))

    if not os.path.exists(libcrypto_path):
        raise LibraryNotFoundError('libcrypto does not exist at %s' % libcrypto_path)

    if not os.path.exists(libssl_path):
        raise LibraryNotFoundError('libssl does not exist at %s' % libssl_path)

    if trust_list_path is not None:
        if not isinstance(trust_list_path, str_cls):
            raise ValueError('trust_list_path must be a unicode string, not %s' % type_name(trust_list_path))
        if not os.path.exists(trust_list_path):
            raise OSError('trust_list_path does not exist at %s' % trust_list_path)

    with _backend_lock:
        if _module_values['backend'] is not None:
            raise RuntimeError('Another part of oscrypto has already been imported, unable to force use of OpenSSL')

        _module_values['backend'] = 'openssl'
        _module_values['backend_config'] = {
            'libcrypto_path': libcrypto_path,
            'libssl_path': libssl_path,
            'trust_list_path': trust_list_path,
        }
