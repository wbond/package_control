import sys
import os

if os.name == 'nt':
    from ctypes import windll, create_unicode_buffer

import sublime


def add_to_path(path):
    # Python 2.x on Windows can't properly import from non-ASCII paths, so
    # this code added the DOC 8.3 version of the lib folder to the path in
    # case the user's username includes non-ASCII characters
    if os.name == 'nt':
        buf = create_unicode_buffer(512)
        if windll.kernel32.GetShortPathNameW(path, buf, len(buf)):
            path = buf.value

    if path not in sys.path:
        sys.path.append(path)


lib_folder = os.path.join(sublime.packages_path(), 'Package Control', 'lib')
add_to_path(os.path.join(lib_folder, 'all'))

if os.name == 'nt':
    add_to_path(os.path.join(lib_folder, 'windows'))
