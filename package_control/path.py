import os

import sublime


def cache_path():
    """
    Return Package Control cache path

    By using the cached value RPC calls between sublime_text and plugin_host
    are avoided, which reduces the time to get the value by 2000 times.

    As `sublime.cache_path()` doesn't return a value until the plugin_host
    was loaded, this function is required to return a value and initiate the
    cache on demand, rather then a global constant initiated at import time.

    :returns:
        The fully qualified path of the packages path.
    """
    try:
        return cache_path.cached
    except AttributeError:
        cache_dir = sublime.cache_path()
        assert cache_dir
        cache_path.cached = os.path.join(cache_dir, 'Package Control')
        return cache_path.cached


def executable_path():
    """
    Return cached sublime.executable_path()

    By using the cached value RPC calls between sublime_text and plugin_host
    are avoided, which reduces the time to get the value by 2000 times.

    As `sublime.executable_path()` doesn't return a value until the plugin_host
    was loaded, this function is required to return a value and initiate the
    cache on demand, rather then a global constant initiated at import time.

    :returns:
        The fully qualified path of the sublime_text executable path.
    """
    try:
        return executable_path.cached
    except AttributeError:
        executable_path.cached = sublime.executable_path()
        assert executable_path.cached
        return executable_path.cached


def default_packages_path():
    """
    Return cached default packages path

    By using the cached value RPC calls between sublime_text and plugin_host
    are avoided, which reduces the time to get the value by 2000 times.

    As `sublime.executable_path()` doesn't return a value until the plugin_host
    was loaded, this function is required to return a value and initiate the
    cache on demand, rather then a global constant initiated at import time.

    :returns:
        The fully qualified path of the default packages path.
    """
    try:
        return default_packages_path.cached
    except AttributeError:
        default_packages_path.cached = os.path.join(
            os.path.dirname(executable_path()), 'Packages')
        assert default_packages_path.cached
        return default_packages_path.cached


def installed_packages_path():
    """
    Return cached sublime.installed_packages_path()

    By using the cached value RPC calls between sublime_text and plugin_host
    are avoided, which reduces the time to get the value by 2000 times.

    As `sublime.installed_packages_path()` doesn't return a value until the
    plugin_host was loaded, this function is required to return a value and
    initiate the cache on demand, rather then a global constant initiated at
    import time.

    :returns:
        The fully qualified path of the installed packages path.
    """
    try:
        return installed_packages_path.cached
    except AttributeError:
        installed_packages_path.cached = sublime.installed_packages_path()
        assert installed_packages_path.cached
        return installed_packages_path.cached


def unpacked_packages_path():
    """
    Return cached sublime.packages_path()

    By using the cached value RPC calls between sublime_text and plugin_host
    are avoided, which reduces the time to get the value by 2000 times.

    As `sublime.packages_path()` doesn't return a value until the plugin_host
    was loaded, this function is required to return a value and initiate the
    cache on demand, rather then a global constant initiated at import time.

    :returns:
        The fully qualified path of the unpacked packages path.
    """
    try:
        return unpacked_packages_path.cached
    except AttributeError:
        unpacked_packages_path.cached = sublime.packages_path()
        assert unpacked_packages_path.cached
        return unpacked_packages_path.cached


def installed_package_parts(package):
    """
    Return the fully qualified path to and the name of a .sublime-package file.

    :param package:
        The name of the package to return the path for.

    :returns:
        A tuple with the fully qualified path to and
        the name of the .sublime-package file.
    """
    return installed_packages_path(), package + '.sublime-package'


def installed_package_path(package):
    """
    Return the fully qualified path of a .sublime-package file.

    :param package:
        The name of the package to return the path for.

    :returns:
        The fully qualified path of the .sublime-package file.
    """
    return os.path.join(*installed_package_parts(package))


def unpacked_package_path(package):
    """
    Return the fully qualified path of an unpacked package folder.

    :param package:
        The name of the package to return the path for.

    :returns:
        The fully qualified path of the package folder.
    """
    return os.path.join(unpacked_packages_path(), package)
