import sublime
import os
import zipfile

from .console_write import console_write
from .open_compat import open_compat, read_compat
from .unicode import unicode_from_os
from .file_not_found_error import FileNotFoundError


def read_package_file(package, relative_path, binary=False):
    package_dir = _get_package_dir(package)
    file_path = os.path.join(package_dir, relative_path)

    if os.path.exists(package_dir):
        result = _read_regular_file(package, relative_path, binary)
        if result != False:
            return result

    if int(sublime.version()) >= 3000:
        result = _read_zip_file(package, relative_path, binary)
        if result != False:
            return result

    console_write(u"Unable to find file %s in the package %s" % (relative_path, package))
    return False

def package_file_exists(package, relative_path, verbose=True):
    package_dir = _get_package_dir(package)
    file_path = os.path.join(package_dir, relative_path)

    if os.path.exists(package_dir):
        result = _regular_file_exists(package, relative_path)
        if result:
            return result

    if int(sublime.version()) >= 3000:
        return _zip_file_exists(package, relative_path, verbose)

    return False

def _get_package_dir(package):
    """:return: The full filesystem path to the package directory"""

    return os.path.join(sublime.packages_path(), package)

def _read_regular_file(package, relative_path, binary=False):
    package_dir = _get_package_dir(package)
    file_path = os.path.join(package_dir, relative_path)
    try:
        with open_compat(file_path, ('rb' if binary else 'r')) as f:
            return read_compat(f)

    except (FileNotFoundError) as e:
        console_write(u"Unable to find file %s in the package folder for package %s" % (relative_path, package))
        return False

def _read_zip_file(package, relative_path, binary=False):
    zip_path = os.path.join(sublime.installed_packages_path(),
        package + '.sublime-package')

    if not os.path.exists(zip_path):
        console_write(u"Unable to find the package file for %s" % package)
        return False

    try:
        package_zip = zipfile.ZipFile(zip_path, 'r')

    except (zipfile.BadZipfile):
        console_write(u'An error occurred while trying to unzip the package file for %s.' % package_name)
        return False

    try:
        contents = package_zip.read(relative_path)
        if not binary:
            contents = contents.decode('utf-8')
        return contents

    except (KeyError) as e:
        console_write(u"Unable to find file %s in the package file for package %s" % (relative_path, package))

    except (IOError) as e:
        message = unicode_from_os(e)
        console_write(u'Unable to read file from package named %s due to an invalid filename' % path, True)

    except (UnicodeDecodeError):
        console_write(u'Unable to read file from package named %s due to an invalid filename or character encoding issue' % path, True)

    return False

def _regular_file_exists(package, relative_path):
    package_dir = _get_package_dir(package)
    file_path = os.path.join(package_dir, relative_path)
    return os.path.exists(file_path)

def _zip_file_exists(package, relative_path, verbose):
    zip_path = os.path.join(sublime.installed_packages_path(),
        package + '.sublime-package')

    if not os.path.exists(zip_path):
        if verbose:
            console_write(u"Unable to find the package file for %s" % package)
        return False

    try:
        package_zip = zipfile.ZipFile(zip_path, 'r')

    except (zipfile.BadZipfile):
        console_write(u'An error occurred while trying to unzip the package file for %s.' % package_name)
        return False

    try:
        package_zip.getinfo(relative_path)
        return True

    except (KeyError) as e:
        return False
