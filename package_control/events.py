import threading

import sublime



# This ensures we don't run into issues calling the event tracking methods
# from threads
_lock = threading.Lock()


# A dict tracking events for packages being controlled via Package Control
_tracker = {
    # key is package name, value is installed version
    'install': {},
    # key is package name, value is version being upgraded from
    'pre_upgrade': {},
    # key is package name, value is version being upgraded to
    'post_upgrade': {},
    # key is package name, value is installed version
    'remove': {}
}


def add(type, package, version):
    """
    Add a version to the tracker with the version specified

    :param type:
        The type of the tracker event: install, pre_upgrade, post_upgrade or
        remove

    :param package:
        The package name

    :param version:
        The version of the package the event is for
    """

    _lock.acquire()
    _tracker[type][package] = version
    _lock.release()


def clear(type, package, future=False):
    """
    Clears an event from the tracker, possibly in the future. Future clears
    are useful for 'install' and 'post_upgrade' events since we don't have a
    natural event to clear the data on. Thus we set a timeout for 5 seconds in
    the future.

    :param type:
        The type of event to clear

    :param package:
        The name of the package to clear the event info for

    :param future:
        If the clear should happen in 5 seconds, instead of immediately
    """

    def do_clear():
        _lock.acquire()
        del _tracker[type][package]
        _lock.release()
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

    if name not in _tracker['install']:
        return False

    return _tracker['install'][name]


def pre_upgrade(name):
    """
    Check if a package is about to be upgraded (in plugin_unloaded())

    :param name:
        The name of the package to check

    :return:
        A unicode string of the version being upgraded from or
        False if not being upgraded
    """

    if name not in _tracker['pre_upgrade']:
        return False

    return _tracker['pre_upgrade'][name]


def post_upgrade(name):
    """
    Check if a package was just upgraded (in plugin_loaded())

    :param name:
        The name of the package to check

    :return:
        A unicode string of the version upgraded to or
        False if not just upgraded
    """

    if name not in _tracker['post_upgrade']:
        return False

    return _tracker['post_upgrade'][name]


def remove(name):
    """
    Check if a package is about to be removed (in plugin_unloaded())

    :param name:
        The name of the package to check

    :return:
        A unicode string of the version about to be removed or
        False if not being removed
    """

    if name not in _tracker['remove']:
        return False

    return _tracker['remove'][name]
