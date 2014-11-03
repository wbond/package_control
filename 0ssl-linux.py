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


def install_ssl():
    correct_hash = u'a3d44e282d998f4b0391775a88689274d4974dd5ebb0af5207b796862709938b'
    url = u'http://packagecontrol.io/ssl-linux.sublime-package'

    packages_dir = get_sublime_text_dir('Packages')
    if not packages_dir:
        return
    package_dir = os.path.join(packages_dir, 'ssl-linux')

    # The package has already been installed
    if os.path.exists(package_dir):
        return

    opener = urllib2.build_opener(urllib2.ProxyHandler())
    urllib2.install_opener(opener)

    print(u'Package Control: Downloading _ssl modules for Linux')
    f = urllib2.urlopen(url)
    data = f.read()
    f.close()
    print(u'Package Control: Successfully downloaded _ssl modules for Linux')

    data_io = BytesIO(data)

    data_hash = hashlib.sha256(data).hexdigest()
    if data_hash != correct_hash:
        print(u'Package Control: Error validating _ssl modules download (got %s instead of %s)' % (data_hash, correct_hash))
        return

    try:
        data_zip = zipfile.ZipFile(data_io, 'r')
    except (zipfile.BadZipfile):
        print(u'Package Control: Error unzipping _ssl modules package file')
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
        import imp

        try:
            # Python 2
            str_cls = unicode
            st_version = 2
            package_dir = os.getcwd()
        except (NameError):
            str_cls = str
            st_version = 3
            package_dir = os.path.dirname(__file__)


        if sublime.platform() == 'linux':
            # We use this construct because in ST2 the package will be in Packages/, but
            # in ST3 it will be in Installed Packages/.
            cur_package_dir = os.path.dirname(package_dir)
            try:
                if not isinstance(cur_package_dir, str_cls):
                    cur_package_dir = cur_package_dir.decode('utf-8', 'strict')

                modules_dir = os.path.join(cur_package_dir, u'../Packages/ssl-linux')
                modules_dir = os.path.normpath(modules_dir)

                arch_lib_path = os.path.join(modules_dir,
                    'st%d_linux_%s' % (st_version, sublime.arch()))

                print(u'Linux SSL: enabling custom linux ssl module')

                for ssl_ver in [u'1.0.0', u'10', u'0.9.8']:

                    lib_path = os.path.join(arch_lib_path, u'libssl-%s' % ssl_ver)
                    if st_version == 2:
                        lib_path = lib_path.encode('utf-8')
                    sys.path.append(lib_path)

                    try:
                        import _ssl
                        print(u'Linux SSL: successfully loaded _ssl module for libssl.so.%s' % ssl_ver)
                    except (ImportError) as e:
                        print(u'Linux SSL: _ssl module import error - %s' % str_cls(e))
                        continue

                    try:
                        if st_version == 2:
                            plat_lib_path = os.path.join(modules_dir, u'st2_linux')
                            m_info = imp.find_module('ssl', [plat_lib_path])
                            m = imp.load_module('ssl', *m_info)
                        else:
                            import ssl
                        break
                    except (ImportError) as e:
                        print(u'Linux SSL: ssl module import error - %s' % str_cls(e))

                if st_version == 2:
                    if 'httplib' in sys.modules:
                        print(u'Linux SSL: unloading httplib module so ssl will be available')
                        del sys.modules['httplib']

                else:
                    if 'http' in sys.modules:
                        print(u'Linux SSL: unloading http module so ssl will be available')
                        del sys.modules['http']
                        del sys.modules['http.client']
                    if 'urllib' in sys.modules:
                        print(u'Linux SSL: unloading urllib module so ssl will be available')
                        del sys.modules['urllib']
                        del sys.modules['urllib.request']

            except (UnicodeDecodeError):
                print(u'Linux SSL: Error decoding package path as UTF-8')

    """

    inject_code = dedent(inject_code)

    if sys.version_info < (3,):
        package_dir = os.path.join(packages_dir, '0ssl-linux')

        if not os.path.exists(package_dir):
            os.mkdir(package_dir, 0o755)

        filename = os.path.join(package_dir, 'inject.py')
        with open(filename, 'wb') as f:
            f.write(inject_code.encode('utf-8'))

    else:
        installed_packages_dir = get_sublime_text_dir('Installed Packages')
        if not installed_packages_dir:
            return

        filename = os.path.join(installed_packages_dir, '0ssl-linux.sublime-package')

        with zipfile.ZipFile(filename, 'w') as z:
            z.writestr('inject.py', inject_code.encode('utf-8'))

    print(u'Package Control: Successfully installed _ssl modules for Linux')
    def show_restart():
        sublime.message_dialog(u'Package Control\n\n'
            u'Package Control just installed the missing Python _ssl ' + \
            u'module for Linux since Sublime Text does not include it.\n\n' + \
            u'Please restart Sublime Text to make SSL available to all ' + \
            u'packages.')
    sublime.set_timeout(show_restart, 100)


if sublime.platform() == 'linux':
    threading.Thread(target=install_ssl).start()
