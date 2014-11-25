import sys
import threading

import sublime

if sys.version_info < (3,):
    from package_control.bootstrap import bootstrap_early_package
    from package_control.package_manager import PackageManager
else:
    from .package_control.bootstrap import bootstrap_early_package
    from .package_control.package_manager import PackageManager


def plugin_loaded():
    manager = PackageManager()
    settings = manager.settings.copy()

    # SSL support fo Linux
    if sublime.platform() == 'linux':
        linux_ssl_name = u'_ssl modules for Linux'
        linux_ssl_url = u'http://packagecontrol.io/ssl-linux.sublime-package'
        linux_ssl_hash = u'd12a2ca2843b3c06a834652e9827a29f88872bb31bd64230775f3dbe12e0ebd4'
        linux_ssl_priority = u'000'
        linux_ssl_inject_code = u"""
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

        def linux_ssl_show_restart():
            sublime.message_dialog(u'Package Control\n\n'
                u'Package Control just installed the missing Python _ssl ' + \
                u'module for Linux since Sublime Text does not include it.\n\n' + \
                u'Please restart Sublime Text to make SSL available to all ' + \
                u'packages.')

        linux_ssl_args = (settings, linux_ssl_name, linux_ssl_url,
            linux_ssl_hash, linux_ssl_priority, linux_ssl_inject_code,
            linux_ssl_show_restart)
        threading.Thread(target=bootstrap_early_package, args=linux_ssl_args).start()


    # SSL support for SHA-2 certificates with ST2 on Windows
    if sublime.platform() == 'windows' and sys.version_info < (3,):
        win_ssl_name = u'_ssl modules for ST2 on Windows'
        win_ssl_url = u'http://packagecontrol.io/ssl-windows.sublime-package'
        win_ssl_hash = u'1d1a129fe0655d765e839fe4b81a0fb9eeb0ba0fbb78489154e65b5ffb4cad9d'
        win_ssl_priority = u'000'
        win_ssl_inject_code = u"""
            import sublime
            import os
            import sys

            # This patch is only for Python 2 on Windows
            if os.name == 'nt' and sys.version_info < (3,):
                package_dir = os.getcwd()
                modules_dir = os.path.join(os.path.dirname(package_dir), 'ssl-windows')
                if not isinstance(modules_dir, unicode):
                    modules_dir = modules_dir.decode('utf-8', 'strict')
                modules_dir = os.path.normpath(modules_dir)

                arch_lib_path = os.path.join(modules_dir,
                    'st2_windows_%s' % sublime.arch())

                sys.path.insert(0, arch_lib_path)
        """

        def win_ssl_show_restart():
            sublime.message_dialog(u'Package Control\n\n'
                u'Package Control just upgraded the Python _ssl module for ' + \
                u'ST2 on Windows because the bundled one does not include ' + \
                u'support for modern SSL certificates.\n\n' + \
                u'Please restart Sublime Text to complete the upgrade.')

        win_ssl_args = (settings, win_ssl_name, win_ssl_url, win_ssl_hash,
            win_ssl_priority, win_ssl_inject_code, win_ssl_show_restart)
        threading.Thread(target=bootstrap_early_package, args=win_ssl_args).start()


    # bzip2 modules for better compression
    bz2_name = u'bz2 modules'
    bz2_url = u'http://packagecontrol.io/bz2.sublime-package'
    bz2_hash = u'd403c7e7c177287047dfba7730c4cb42e06f770b3014e1a43d2d1a72392e9a7b'
    bz2_priority = u'001'
    bz2_inject_code = u"""
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

            try:
                import bz2
            except (ImportError):
                pass
    """

    bz2_args = (settings, bz2_name, bz2_url, bz2_hash, bz2_priority,
        bz2_inject_code, None)
    threading.Thread(target=bootstrap_early_package, args=bz2_args).start()


# ST2 compat
if sys.version_info < (3,):
    plugin_loaded()
