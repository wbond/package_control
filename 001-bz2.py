import sys
import threading

import sublime

if sys.version_info < (3,):
    from package_control.bootstrap import bootstrap_early_package
else:
    from .package_control.bootstrap import bootstrap_early_package



name = u'bz2 modules'
url = u'http://packagecontrol.io/bz2.sublime-package'
hash_ = u'42b641b64ffa5dd52c0c2bbdc935532b92a34bf2d89f1077ef4fccd35928734b'
priority = u'001'
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

        try:
            import bz2
        except (ImportError):
            pass
"""


args = (name, url, hash_, priority, inject_code, None)
threading.Thread(target=bootstrap_early_package, args=args).start()
