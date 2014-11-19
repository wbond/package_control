import sys
import threading

import sublime

if sys.version_info < (3,):
    from package_control.bootstrap import bootstrap_early_package
else:
    from .package_control.bootstrap import bootstrap_early_package



name = u'_ssl modules for Linux'
url = u'http://packagecontrol.io/ssl-linux.sublime-package'
hash_ = u'a3d44e282d998f4b0391775a88689274d4974dd5ebb0af5207b796862709938b'
priority = u'000'
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

def show_restart():
    sublime.message_dialog(u'Package Control\n\n'
        u'Package Control just installed the missing Python _ssl ' + \
        u'module for Linux since Sublime Text does not include it.\n\n' + \
        u'Please restart Sublime Text to make SSL available to all ' + \
        u'packages.')


if sublime.platform() == 'linux':
    args = (name, url, hash_, priority, inject_code, show_restart)
    threading.Thread(target=bootstrap_early_package, args=args).start()
