import zipfile
import os
import hashlib
import sys
from os import path
from textwrap import dedent
try:
    import urllib2
    from urlparse import urlparse
    str_cls = unicode
    from cStringIO import StringIO as BytesIO
    package_control_subdir = os.getcwd()
except (ImportError) as e:
    import urllib.request as urllib2
    from urllib.parse import urlparse
    str_cls = str
    from io import BytesIO
    package_control_subdir = path.dirname(__file__)
# Prevents an unknown encoding error that occurs when first using
# urllib(2) in a thread.
import encodings.idna

import sublime


def get_sublime_text_dir(name):
    cur_packages_dir = path.dirname(path.dirname(package_control_subdir))

    try:
        if not isinstance(cur_packages_dir, str_cls):
            cur_packages_dir = cur_packages_dir.decode('utf-8', 'strict')
        return path.normpath(path.join(cur_packages_dir, '..', name))

    except (UnicodeDecodeError):
        print(u'Package Control: An error occurred decoding the Package Control path as UTF-8')
        return


def bootstrap_early_package(name, url, hash_, priority, inject_code, on_complete):
    """
    Downloads packages that need to be injected early in the Sublime Text
    load process so that other packages can use them.

    :param name:
        The user-friendly name for status messages

    :param url:
        The non-secure URL to download from

    :param hash_:
        The sha256 hash of the package file

    :param priority:
        A three-digit number that controls what order packages are
        injected in

    :param inject_code:
        The python code to inject the package into sys.path

    :param on_complete:
        A callback to be run in the main Sublime thread, so it can use the API
    """

    package_filename = path.basename(urlparse(url).path)
    package_basename, _ = path.splitext(package_filename)

    packages_dir = get_sublime_text_dir('Packages')
    if not packages_dir:
        return
    package_dir = path.join(packages_dir, package_basename)

    # The package has already been installed
    if path.exists(package_dir):
        return

    opener = urllib2.build_opener(urllib2.ProxyHandler())
    urllib2.install_opener(opener)

    print(u'Package Control: Downloading %s' % name)
    f = urllib2.urlopen(url)
    data = f.read()
    f.close()
    print(u'Package Control: Successfully downloaded %s' % name)

    data_io = BytesIO(data)

    data_hash = hashlib.sha256(data).hexdigest()
    if data_hash != hash_:
        print(u'Package Control: Error validating %s (got %s instead of %s)' % (name, data_hash, hash_))
        return

    try:
        data_zip = zipfile.ZipFile(data_io, 'r')
    except (zipfile.BadZipfile):
        print(u'Package Control: Error unzipping %s' % package_filename)
        return

    if not path.exists(package_dir):
        os.mkdir(package_dir, 0o755)

    for zip_path in data_zip.namelist():
        dest = zip_path

        if not isinstance(dest, str_cls):
            dest = dest.decode('utf-8', 'strict')

        dest = dest.replace('\\', '/')

        dest = path.join(package_dir, dest)

        if dest[-1] == '/':
            if not path.exists(dest):
                os.mkdir(dest, 0o755)
        else:
            dest_dir = path.dirname(dest)
            if not path.exists(dest_dir):
                os.mkdir(dest_dir, 0o755)

            with open(dest, 'wb') as f:
                f.write(data_zip.read(zip_path))

    data_zip.close()

    inject_code = dedent(inject_code).strip() + '\n'

    if sys.version_info < (3,):
        package_dir = path.join(packages_dir, '%s-%s' % (priority, package_basename))

        if not path.exists(package_dir):
            os.mkdir(package_dir, 0o755)

        filename = path.join(package_dir, 'inject.py')
        with open(filename, 'wb') as f:
            f.write(inject_code.encode('utf-8'))

    else:
        installed_packages_dir = get_sublime_text_dir('Installed Packages')
        if not installed_packages_dir:
            return

        filename = path.join(installed_packages_dir, '%s-%s.sublime-package' % (priority, package_basename))

        with zipfile.ZipFile(filename, 'w') as z:
            z.writestr('inject.py', inject_code.encode('utf-8'))

    print(u'Package Control: Successfully installed %s' % name)

    if on_complete:
        sublime.set_timeout(on_complete, 100)
