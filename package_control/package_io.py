import os
import zipfile

from . import sys_path
from .console_write import console_write


def create_empty_file(filename):
    """
    Creates an empty file if it does not exist.

    The main use case is to create empty cookie files, such as
    ``package-control.cleanup`` without throwing exceptions.

    :param filename:
        The absolute path of the file to create.

    :returns:
        True, if file exists or is successfully created
        False, if file couldn't be created
    """

    try:
        open(filename, 'xb').close()
    except FileExistsError:
        pass
    except (OSError, IOError) as e:
        console_write('Unable to create %s: %s', (filename, e))
        return False
    return True


def list_sublime_package_dirs(path):
    """
    Return a set of directories in the folder specified that are not
    hidden and are not marked to be removed

    :param path:
        The folder to list the directories inside of

    :return:
        A generator of directory names
    """

    try:
        for filename in os.listdir(path):
            if filename[0] == '.':
                continue
            file_path = os.path.join(path, filename)
            # Don't include files
            if not os.path.isdir(file_path):
                continue
            # Don't include hidden packages
            if os.path.exists(os.path.join(file_path, '.hidden-sublime-package')):
                continue
            # Don't include a dir if it is going to be cleaned up
            if os.path.exists(os.path.join(file_path, 'package-control.cleanup')):
                continue
            yield filename

    except FileNotFoundError:
        pass


def list_sublime_package_files(path):
    """
    Return a set of all .sublime-package files in a folder

    :param path:
        The directory to look in for .sublime-package files

    :return:
        A generator of package names with .sublime-package suffix removed
    """

    try:
        for filename in os.listdir(path):
            name, ext = os.path.splitext(filename)
            if ext.lower() != '.sublime-package':
                continue
            file_path = os.path.join(path, filename)
            if not os.path.isfile(file_path):
                continue
            yield name

    except FileNotFoundError:
        pass


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

    if regular_file_exists(package, relative_path):
        return _read_regular_file(package, relative_path, binary)

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

    return regular_file_exists(package, relative_path) or zip_file_exists(package, relative_path)


def get_package_cache_dir(package):
    """
    Return the absolute path of the package's cache directory.

    :param package:
        The package name to return path for.

    :return:
        The full filesystem path to the package's cache directory
    """

    return os.path.join(sys_path.cache_path(), package)


def get_package_module_cache_dir(package):
    """
    Return the absolute path of the package's python modules cache directory.

    Relevant for python 3.8 plugins only.

    :param package:
        The package name to return path for.

    :return:
        The full filesystem path to the package's python module cache directory
    """

    return os.path.join(sys_path.python_packages_cache_path(), package)


def get_package_dir(package):
    """
    Return the absolute path of the package.

    :param package:
        The package name to return path for.

    :return:
        The full filesystem path to the package directory
    """

    return os.path.join(sys_path.packages_path(), package)


def get_installed_package_path(package):
    """
    Generate the absolute sublime-package file path of a package.

    :param package:
        The package name to return path for.

    :return:
        The full filesystem path to the sublime-package file
    """

    return os.path.join(sys_path.installed_packages_path(), package + '.sublime-package')


def _read_regular_file(package, relative_path, binary=False):
    package_dir = get_package_dir(package)
    file_path = os.path.join(package_dir, relative_path)

    mode, encoding = ('rb', None) if binary else ('r', 'utf-8')
    with open(file_path, mode=mode, encoding=encoding) as fobj:
        return fobj.read()


def _read_zip_file(package, relative_path, binary=False):
    zip_path = get_installed_package_path(package)

    if not os.path.exists(zip_path):
        return False

    try:
        package_zip = zipfile.ZipFile(zip_path, 'r')

    except (zipfile.BadZipfile):
        console_write(
            '''
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
            '''
            Unable to read file from sublime-package file for %s due to the
            package file being corrupt
            ''',
            package
        )

    except (IOError):
        console_write(
            '''
            Unable to read file from sublime-package file for %s due to an
            invalid filename
            ''',
            package
        )

    except (UnicodeDecodeError):
        console_write(
            '''
            Unable to read file from sublime-package file for %s due to an
            invalid filename or character encoding issue
            ''',
            package
        )

    return False


def regular_file_exists(package, relative_path):
    package_dir = get_package_dir(package)
    file_path = os.path.join(package_dir, relative_path)
    return os.path.exists(file_path)


def zip_file_exists(package, relative_path):
    zip_path = get_installed_package_path(package)

    if not os.path.exists(zip_path):
        return False

    try:
        package_zip = zipfile.ZipFile(zip_path, 'r')

    except (zipfile.BadZipfile):
        console_write(
            '''
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
