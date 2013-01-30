import sublime


def show_error(string):
    """
    Displays an error message with a standard "Package Control" header

    :param string:
        The error to display
    """

    sublime.error_message(u'Package Control\n\n%s' % string)
