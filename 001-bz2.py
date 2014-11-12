import zipfile
import os
import hashlib
import sys
import threading
from textwrap import dedent
try:
    import urllib2
    str_cls = unicode
    from cStringIO import StringIO as BytesIO
    package_control_dir = os.getcwd()
except (ImportError):
    import urllib.request as urllib2
    str_cls = str
    from io import BytesIO
    package_control_dir = os.path.dirname(__file__)
# Prevents an unknown encoding error that occurs when first using
# urllib(2) in a thread.
import encodings.idna

import sublime


def get_sublime_text_dir(name):
    cur_package_dir = os.path.dirname(package_control_dir)

    try:
        if not isinstance(cur_package_dir, str_cls):
            cur_package_dir = cur_package_dir.decode('utf-8', 'strict')
        return os.path.normpath(os.path.join(cur_package_dir, '..', name))

    except (UnicodeDecodeError):
        print(u'Package Control: An error occurred decoding the Package Control path as UTF-8')
        return


def install_bz2():
    correct_hash = u'226558bc121d4865c729539ad060c282379c39a42ab7aad59ab9f74aac0013a8'
    url = u'http://packagecontrol.io/bz2.sublime-package'

    packages_dir = get_sublime_text_dir('Packages')
    if not packages_dir:
        return
    package_dir = os.path.join(packages_dir, 'bz2')

    # The package has already been installed
    if os.path.exists(package_dir):
        return

    opener = urllib2.build_opener(urllib2.ProxyHandler())
    urllib2.install_opener(opener)

    print(u'Package Control: Downloading bz2 modules')
    f = urllib2.urlopen(url)
    data = f.read()
    f.close()
    print(u'Package Control: Successfully downloaded bz2 modules')

    data_io = BytesIO(data)

    data_hash = hashlib.sha256(data).hexdigest()
    if data_hash != correct_hash:
        print(u'Package Control: Error validating bz2 modules download (got %s instead of %s)' % (data_hash, correct_hash))
        return

    try:
        data_zip = zipfile.ZipFile(data_io, 'r')
    except (zipfile.BadZipfile):
        print(u'Package Control: Error unzipping bz2 modules package file')
        return

    if not os.path.exists(package_dir):
        os.mkdir(package_dir, 0o755)

    for path in data_zip.namelist():
        dest = path

        if not isinstance(dest, str_cls):
            dest = dest.decode('utf-8', 'strict')

        dest = dest.replace('\\', '/')

        dest = os.path.join(package_dir, dest)

        if dest[-1] == '/':
            if not os.path.exists(dest):
                os.mkdir(dest, 0o755)
        else:
            dest_dir = os.path.dirname(dest)
            if not os.path.exists(dest_dir):
                os.mkdir(dest_dir, 0o755)

            with open(dest, 'wb') as f:
                f.write(data_zip.read(path))

    data_zip.close()

    inject_code = u"""
        import sublime
        import os
        import sys

        try:
            # Python 2
            str_cls = unicode
            st_version = 2
            package_dir = os.getcwd()
        except (NameError):
            str_cls = str
            st_version = 3
            package_dir = os.path.dirname(__file__)


        try:
            import bz2
        except (ImportError):
            cur_package_dir = os.path.dirname(package_dir)

            if not isinstance(cur_package_dir, str_cls):
                cur_package_dir = cur_package_dir.decode('utf-8', 'strict')

            modules_dir = os.path.join(cur_package_dir, u'../Packages/bz2')
            modules_dir = os.path.normpath(modules_dir)

            arch_lib_path = os.path.join(modules_dir,
                'st%d_%s_%s' % (st_version, sublime.platform(), sublime.arch()))

            sys.path.append(arch_lib_path)

            import bz2

    """

    inject_code = dedent(inject_code)

    if sys.version_info < (3,):
        package_dir = os.path.join(packages_dir, '001-bz2')

        if not os.path.exists(package_dir):
            os.mkdir(package_dir, 0o755)

        filename = os.path.join(package_dir, 'inject.py')
        with open(filename, 'wb') as f:
            f.write(inject_code.encode('utf-8'))

    else:
        installed_packages_dir = get_sublime_text_dir('Installed Packages')
        if not installed_packages_dir:
            return

        filename = os.path.join(installed_packages_dir, '001-bz2.sublime-package')

        with zipfile.ZipFile(filename, 'w') as z:
            z.writestr('inject.py', inject_code.encode('utf-8'))

    print(u'Package Control: Successfully installed bz2 modules')


threading.Thread(target=install_bz2).start()
