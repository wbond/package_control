import os
import zipfile

import sublime

from . import logger
log = logger.get(__name__)

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

    log.debug(u"Unable to find file %s in the package %s", relative_path, package)
    return False


def package_file_exists(package, relative_path):
    package_dir = _get_package_dir(package)
    file_path = os.path.join(package_dir, relative_path)

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
    try:
        with open_compat(file_path, ('rb' if binary else 'r')) as f:
            return read_compat(f)

    except (FileNotFoundError) as e:
        log.debug(u"Unable to find file %s in the package folder for %s", relative_path, package)
        return False


def _read_zip_file(package, relative_path, binary=False):
    zip_path = os.path.join(sublime.installed_packages_path(),
        package + '.sublime-package')

    if not os.path.exists(zip_path):
        log.debug(u"Unable to find a sublime-package file for %s", package)
        return False

    try:
        package_zip = zipfile.ZipFile(zip_path, 'r')

    except (zipfile.BadZipfile):
        log.warning(u'An error occurred while trying to unzip the sublime-package file for %s.', package)
        return False

    try:
        contents = package_zip.read(relative_path)
        if not binary:
            contents = contents.decode('utf-8')
        return contents

    except (KeyError) as e:
        log.debug(u"Unable to find file %s in the sublime-package file for %s", relative_pat, package)

    except (IOError) as e:
        message = unicode_from_os(e)
        log.warning(u'Unable to read file from sublime-package file for %s due to an invalid filename', package)

    except (UnicodeDecodeError):
        log.warning(u'Unable to read file from sublime-package file for %s due to an invalid filename or character encoding issue', package)

    return False


def _regular_file_exists(package, relative_path):
    package_dir = _get_package_dir(package)
    file_path = os.path.join(package_dir, relative_path)
    return os.path.exists(file_path)


def _zip_file_exists(package, relative_path):
    zip_path = os.path.join(sublime.installed_packages_path(),
        package + '.sublime-package')

    if not os.path.exists(zip_path):
        return False

    try:
        package_zip = zipfile.ZipFile(zip_path, 'r')

    except (zipfile.BadZipfile):
        log.warning(u'An error occurred while trying to unzip the sublime-package file for %s.', package_name)
        return False

    try:
        package_zip.getinfo(relative_path)
        return True

    except (KeyError) as e:
        return False
