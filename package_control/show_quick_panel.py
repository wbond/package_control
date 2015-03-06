import sublime


def show_quick_panel(window, *args, **kwargs):
    """
    Wrapper for the window.show_quick_panel API that keeps it open.

    Accepts same parameters as window.show_quick_panel, plus:

    :param window:
        Same as for window.show_quick_panel
    """
    if int(sublime.version()) >= 3070:
        # Override the flags parameter to include the KEEP_OPEN_ON_FOCUS_LOST
        # flag
        import inspect
        sig = inspect.signature(window.show_quick_panel)
        ba = sig.bind(*args, **kwargs)
        ba.arguments['flags'] = (ba.arguments.get('flags', 0)
                                 | sublime.KEEP_OPEN_ON_FOCUS_LOST)
        args, kwargs = ba.args, ba.kwargs

    return window.show_quick_panel(*args, **kwargs)
