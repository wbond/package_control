import locale
import sys
import tempfile
import os

if sys.platform == 'win32':
    import ctypes

try:
    str_cls = unicode
except (NameError):
    str_cls = str

# Sublime Text on OS X does not seem to report the correct encoding
# so we hard-code that to UTF-8
_encoding = 'utf-8' if sys.platform == 'darwin' else locale.getpreferredencoding()

_fallback_encodings = ['utf-8', 'cp1252']


def unicode_from_os(e):
    """
    This is needed as some exceptions coming from the OS are
    already encoded and so just calling unicode(e) will result
    in an UnicodeDecodeError as the string isn't in ascii form.

    :param e:
        The exception to get the value of

    :return:
        The unicode version of the exception message
    """

    if sys.version_info >= (3,):
        return str(e)

    try:
        if isinstance(e, Exception):
            e = e.args[0]

        if isinstance(e, str_cls):
            return e

        if isinstance(e, int):
            e = str(e)

        return str_cls(e, _encoding)

    # If the "correct" encoding did not work, try some defaults, and then just
    # obliterate characters that we can't seen to decode properly
    except UnicodeDecodeError:
        for encoding in _fallback_encodings:
            try:
                return str_cls(e, encoding, errors='strict')
            except:
                pass
    return str_cls(e, errors='replace')


def tempfile_unicode_patch():
    """
    This function monkey-patches the tempfile module in ST2 on Windows to
    properly handle non-ASCII paths from environmental variables being
    used as the basis for a temp directory.
    """

    if sys.version_info >= (3,):
        return

    if sys.platform != 'win32':
        return

    if hasattr(tempfile._candidate_tempdir_list, 'patched'):
        return

    unicode_error = False
    for var in ['TMPDIR', 'TEMP', 'TMP']:
        dir_ = os.getenv(var)
        if not dir_:
            continue
        # If the path contains a non-unicode chars that is also
        # non-ASCII, then this will fail
        try:
            dir_ + u''
        except (UnicodeDecodeError):
            unicode_error = True
            break
        # Windows paths can not contain a ?, so this is evidence
        # that a unicode deocding issue happened
        if dir_.find('?') != -1:
            unicode_error = True
            break

    if not unicode_error:
        return

    kernel32 = ctypes.windll.kernel32

    kernel32.GetEnvironmentStringsW.argtypes = []
    kernel32.GetEnvironmentStringsW.restype = ctypes.c_void_p

    str_pointer = kernel32.GetEnvironmentStringsW()
    string = ctypes.wstring_at(str_pointer)

    env_vars = {}
    while string != '':
        if string[0].isalpha():
            name, value = string.split(u'=', 1)
            env_vars[name.encode('ascii')] = value
        # Include the trailing null byte, and measure each
        # char as 2 bytes since Windows uses UTF-16 for
        # wide chars
        str_pointer += (len(string) + 1) * 2

        string = ctypes.wstring_at(str_pointer)

    # This is pulled from tempfile.py in Python 2.6 and patched to grab the
    # temp path environmental variables as unicode from the call to
    # GetEnvironmentStringsW()
    def _candidate_tempdir_list():
        dirlist = []

        # First, try the environment.
        for envname in 'TMPDIR', 'TEMP', 'TMP':
            dirname = env_vars.get(envname)
            if dirname:
                dirlist.append(dirname)

        # Failing that, try OS-specific locations.
        if os.name == 'riscos':
            dirname = os.getenv('Wimp$ScrapDir')
            if dirname:
                dirlist.append(dirname)
        elif os.name == 'nt':
            dirlist.extend([r'c:\temp', r'c:\tmp', r'\temp', r'\tmp'])
        else:
            dirlist.extend(['/tmp', '/var/tmp', '/usr/tmp'])

        # As a last resort, the current directory.
        try:
            dirlist.append(os.getcwd())
        except (AttributeError, os.error):
            dirlist.append(os.curdir)

        return dirlist

    tempfile._candidate_tempdir_list = _candidate_tempdir_list
    setattr(tempfile._candidate_tempdir_list, 'patched', True)
