import os
import zipfile

from .console_write import console_write
from .path import installed_package_path
from .path import unpacked_package_path


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

    try:
        return _read_regular_file(package, relative_path, binary)
    except FileNotFoundError:
        return _read_zip_file(package, relative_path, binary)


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

    return _regular_file_exists(package, relative_path) or _zip_file_exists(package, relative_path)


def _read_regular_file(package, relative_path, binary=False):
    file_path = os.path.join(unpacked_package_path(package), relative_path)

    mode, encoding = ('rb', None) if binary else ('r', 'utf-8')
    with open(file_path, mode=mode, encoding=encoding) as f:
        return f.read()


def _read_zip_file(package, relative_path, binary=False):
    try:
        package_zip = zipfile.ZipFile(installed_package_path(package), 'r')

    except (FileNotFoundError):
        return False

    except (zipfile.BadZipfile):
        console_write(
            '''
            An error occurred while trying to unzip the sublime-package file for %s.
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
            '''
            Unable to read file from sublime-package file for %s due to the
            package file being corrupt.
            ''',
            package
        )

    except (IOError):
        console_write(
            '''
            Unable to read file from sublime-package file for %s due to an
            invalid filename.
            ''',
            package
        )

    except (UnicodeDecodeError):
        console_write(
            '''
            Unable to read file from sublime-package file for %s due to an
            invalid filename or character encoding issue.
            ''',
            package
        )

    return False


def _regular_file_exists(package, relative_path):
    file_path = os.path.join(unpacked_package_path(package), relative_path)
    return os.path.exists(file_path)


def _zip_file_exists(package, relative_path):
    try:
        package_zip = zipfile.ZipFile(installed_package_path(package), 'r')

    except (FileNotFoundError):
        return False

    except (zipfile.BadZipfile):
        console_write(
            '''
            An error occurred while trying to unzip the sublime-package file for %s.
            ''',
            package
        )
        return False

    try:
        package_zip.getinfo(relative_path)
        return True

    except (KeyError):
        return False
