import threading

import sublime

INSTALL = 'install'
REMOVE = 'remove'
PRE_UPGRADE = 'pre_upgrade'
POST_UPGRADE = 'post_upgrade'

# This ensures we don't run into issues calling the event tracking methods
# from threads
__lock = threading.Lock()


def _tracker():
    """
    Return event tracker storage object

    Use an unsaved settings object to share events across plugin_hosts.
    """

    try:
        return _tracker.cache
    except AttributeError:
        tracker = sublime.load_settings("Package Control Events")
        if tracker is not None and tracker.settings_id > 0:
            _tracker.cache = tracker
            return tracker
        return {}  # return dummy dictionary until API is ready


def add(event_type, package, version):
    """
    Add a version to the tracker with the version specified

    :param event_type:
        The type of the tracker event: install, pre_upgrade, post_upgrade or
        remove

    :param package:
        The package name

    :param version:
        The version of the package the event is for
    """

    if event_type not in (INSTALL, PRE_UPGRADE, POST_UPGRADE, REMOVE):
        raise KeyError(repr(event_type))

    with __lock:
        tracker = _tracker()
        packages = tracker.get(event_type, {})
        packages[package] = version
        tracker.set(event_type, packages)


def clear(event_type, package, future=False):
    """
    Clears an event from the tracker, possibly in the future. Future clears
    are useful for 'install' and 'post_upgrade' events since we don't have a
    natural event to clear the data on. Thus we set a timeout for 5 seconds in
    the future.

    :param event_type:
        The type of event to clear

    :param package:
        The name of the package to clear the event info for

    :param future:
        If the clear should happen in 5 seconds, instead of immediately
    """

    if event_type not in (INSTALL, PRE_UPGRADE, POST_UPGRADE, REMOVE):
        raise KeyError(repr(event_type))

    def do_clear():
        with __lock:
            tracker = _tracker()
            packages = tracker.get(event_type, {})
            if package in packages:
                del packages[package]
                tracker.set(event_type, packages)

    if future:
        sublime.set_timeout(do_clear, 5000)
    else:
        do_clear()


def install(name):
    """
    Check if a package was just installed (in plugin_loaded())

    :param name:
        The name of the package to check

    :return:
        A unicode string of the version just installed or
        False if not just installed
    """

    with __lock:
        event = _tracker().get(INSTALL) or {}
        return event.get(name, False)


def pre_upgrade(name):
    """
    Check if a package is about to be upgraded (in plugin_unloaded())

    :param name:
        The name of the package to check

    :return:
        A unicode string of the version being upgraded from or
        False if not being upgraded
    """

    with __lock:
        event = _tracker().get(PRE_UPGRADE) or {}
        return event.get(name, False)


def post_upgrade(name):
    """
    Check if a package was just upgraded (in plugin_loaded())

    :param name:
        The name of the package to check

    :return:
        A unicode string of the version upgraded to or
        False if not just upgraded
    """

    with __lock:
        event = _tracker().get(POST_UPGRADE) or {}
        return event.get(name, False)


def remove(name):
    """
    Check if a package is about to be removed (in plugin_unloaded())

    :param name:
        The name of the package to check

    :return:
        A unicode string of the version about to be removed or
        False if not being removed
    """

    with __lock:
        event = _tracker().get(REMOVE) or {}
        return event.get(name, False)
