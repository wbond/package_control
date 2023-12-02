import functools
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
        If all lines should be indented by a set indent after being de-dented
    """

    string = text.format(string, params, strip=strip, indent=indent)
    sublime.set_timeout(functools.partial(sublime.error_message, 'Package Control\n\n' + string), 50)


def show_message(string, params=None, strip=True, indent=None):
    """
    Displays an info message with a standard "Package Control" header after
    running the string through text.format()

    :param string:
        The error to display

    :param params:
        Params to interpolate into the string

    :param strip:
        If the last newline in the string should be removed

    :param indent:
        If all lines should be indented by a set indent after being de-dented
    """

    string = text.format(string, params, strip=strip, indent=indent)
    sublime.set_timeout(functools.partial(sublime.message_dialog, 'Package Control\n\n' + string), 50)
