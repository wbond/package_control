import os
import zipfile

import sublime

from .console_write import console_write
from .open_compat import open_compat, read_compat


def read_package_file(package, relative_path, binary=False):
    """
    Reads the contents of a file that is part of a package

    :param package:
        The name of the package to read from

    :param relative_path:
        The path to the file, relative to the package root

    :param binary:
        If the contents should be read as a byte string instead of a unicode string

    :return:
        A unicode or byte string (depending on value if binary param) or False on error
    """

    if relative_path is None:
        return False

    package_dir = _get_package_dir(package)

    if os.path.exists(package_dir) and _regular_file_exists(package, relative_path):
        return _read_regular_file(package, relative_path, binary)

    if int(sublime.version()) >= 3000:
        result = _read_zip_file(package, relative_path, binary)
        if result is not False:
            return result

    return False


def package_file_exists(package, relative_path):
    """
    Determines if a file exists inside of the package specified. Handles both
    packed and unpacked packages.

    :param package:
        The name of the package to look in

    :param relative_path:
        The path to the file, relative to the package root

    :return:
        A bool - if the file exists
    """

    if relative_path is None:
        return False

    package_dir = _get_package_dir(package)

    if os.path.exists(package_dir):
        result = _regular_file_exists(package, relative_path)
        if result:
            return result

    if int(sublime.version()) >= 3000:
        return _zip_file_exists(package, relative_path)

    return False


def _get_package_dir(package):
    """:return: The full filesystem path to the package directory"""

    return os.path.join(sublime.packages_path(), package)


def _read_regular_file(package, relative_path, binary=False):
    package_dir = _get_package_dir(package)
    file_path = os.path.join(package_dir, relative_path)

    with open_compat(file_path, ('rb' if binary else 'r')) as f:
        return read_compat(f)


def _read_zip_file(package, relative_path, binary=False):
    zip_path = os.path.join(sublime.installed_packages_path(), package + '.sublime-package')

    if not os.path.exists(zip_path):
        return False

    try:
        package_zip = zipfile.ZipFile(zip_path, 'r')

    except (zipfile.BadZipfile):
        console_write(
            u'''
            An error occurred while trying to unzip the sublime-package file
            for %s.
            ''',
            package
        )
        return False

    try:
        contents = package_zip.read(relative_path)
        if not binary:
            contents = contents.decode('utf-8')
        return contents

    except (KeyError):
        pass

    except (zipfile.BadZipfile):
        console_write(
            u'''
            Unable to read file from sublime-package file for %s due to the
            package file being corrupt
            ''',
            package
        )

    except (IOError):
        console_write(
            u'''
            Unable to read file from sublime-package file for %s due to an
            invalid filename
            ''',
            package
        )

    except (UnicodeDecodeError):
        console_write(
            u'''
            Unable to read file from sublime-package file for %s due to an
            invalid filename or character encoding issue
            ''',
            package
        )

    return False


def _regular_file_exists(package, relative_path):
    package_dir = _get_package_dir(package)
    file_path = os.path.join(package_dir, relative_path)
    return os.path.exists(file_path)


def _zip_file_exists(package, relative_path):
    zip_path = os.path.join(sublime.installed_packages_path(), package + '.sublime-package')

    if not os.path.exists(zip_path):
        return False

    try:
        package_zip = zipfile.ZipFile(zip_path, 'r')

    except (zipfile.BadZipfile):
        console_write(
            u'''
            An error occurred while trying to unzip the sublime-package file
            for %s.
            ''',
            package
        )
        return False

    try:
        package_zip.getinfo(relative_path)
        return True

    except (KeyError):
        return False
