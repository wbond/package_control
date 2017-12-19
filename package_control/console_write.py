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
    string = text.format(string, params, strip=strip, indent=indent)
    if prefix:
        print('Package Control:', string)
    else:
        print(string)
