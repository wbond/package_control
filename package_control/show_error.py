import sublime

from . import text


def show_error(string, params=None, strip=True, indent=None):
    """
    Displays an error message with a standard "Package Control" header after
    running the string through text.format()

    :param string:
        The error to display

    :param params:
        Params to interpolate into the string

    :param strip:
        If the last newline in the string should be removed

    :param indent:
        If all lines should be indented by a set indent after being dedented
    """

    string = text.format(string, params, strip=strip, indent=indent)
    sublime.error_message(u'Package Control\n\n%s' % string)
