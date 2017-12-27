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
    sublime.error_message('Package Control\n\n' + string)


def show_message(string, params=None, strip=True, indent=None):
    """
    Displays a message with a standard "Package Control" header after
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
    sublime.message_dialog('Package Control\n\n' + string)


def status_message(string, params=None):
    """
    Displays a message with a standard "Package Control" header after
    running the string through text.format()

    :param string:
        The error to display

    :param params:
        Params to interpolate into the string
    """

    sublime.status_message(text.format(string, params))
