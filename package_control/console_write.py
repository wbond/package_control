import sys

try:
    # Python 2
    str_cls = unicode
except (NameError):
    # Python 3
    str_cls = str

from . import text


def console_write(string, params=None, strip=True, indent=None, prefix=True):
    """
    Writes a value to the Sublime Text console, formatting it for output via
    text.format() and then encoding unicode to utf-8

    :param string:
        The value to write

    :param params:
        Params to interpolate into the string using the % operator

    :param strip:
        If a single trailing newline should be stripped

    :param indent:
        If all lines should be indented by a set indent after being dedented

    :param prefix:
        If the string "Package Control: " should be prefixed to the string
    """

    string = text.format(str_cls(string), params, strip=strip, indent=indent)

    if sys.version_info < (3,):
        if isinstance(string, str_cls):
            string = string.encode('UTF-8')

    if prefix:
        sys.stdout.write('Package Control: ')

    print(string)
