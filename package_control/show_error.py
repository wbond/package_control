import sublime

from . import text
from .console_write import console_write

from threading import Timer

# When there is a batch performance for some chain of execution, and there are error on them,
# we cannot show a error message dialog for each one of them immediately, otherwise we would
# flood the user with messages. See: https://github.com/SublimeTextIssues/Core/issues/1510
is_error_recentely_displayed = False

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

    global is_error_recentely_displayed
    string = text.format(string, params, strip=strip, indent=indent)

    if is_error_recentely_displayed:
        console_write( string )
    else:
        sublime.error_message(u'Package Control\n\n%s' % string)
        is_error_recentely_displayed = True

        # Enable the message dialog after x.x seconds
        thread = Timer(60.0, _restart_error_messages)
        thread.start()

def _restart_error_messages():
    global is_error_recentely_displayed
    is_error_recentely_displayed = False
