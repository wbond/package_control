import sublime


def show_quick_panel(window, items, on_done):
    """
    Wrapper for the window.show_quick_panel API that keeps it open.

    :param window:
        sublime.Window instance where the panel should be shown

    :param items:
        The items to pass to window.show_quick_panel()

    :param on_done:
        The callback to execute when the user has selected an item
    """

    # When possible, keep the quick panel open until the users picks an option
    if int(sublime.version()) >= 3070:
        flags = sublime.KEEP_OPEN_ON_FOCUS_LOST
    else:
        flags = 0

    return window.show_quick_panel(items, on_done, flags)
