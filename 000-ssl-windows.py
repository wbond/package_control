import sys
import threading

import sublime

if sys.version_info < (3,):
    from package_control.bootstrap import bootstrap_early_package
else:
    from .package_control.bootstrap import bootstrap_early_package



name = u'_ssl modules for ST2 on Windows'
url = u'http://packagecontrol.io/ssl-windows.sublime-package'
hash_ = u'3fcde2f193a02576e821db221aeb852790b5dba83f6f2def5818422ce4c08b04'
priority = u'000'
inject_code = u"""
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

def show_restart():
    sublime.message_dialog(u'Package Control\n\n'
        u'Package Control just upgraded the Python _ssl module for ' + \
        u'ST2 on Windows because the bundled one does not include ' + \
        u'support for modern SSL certificates.\n\n' + \
        u'Please restart Sublime Text to complete the upgrade.')


if sublime.platform() == 'windows' and sys.version_info < (3,):
    args = (name, url, hash_, priority, inject_code, show_restart)
    threading.Thread(target=bootstrap_early_package, args=args).start()
