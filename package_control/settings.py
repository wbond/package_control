import sublime


def preferences_filename():
    """
    :return: The appropriate settings filename based on the version of Sublime Text
    """

    return 'Preferences.sublime-settings'


def pc_settings_filename():
    """
    :return: The settings file for Package Control
    """

    return 'Package Control.sublime-settings'


def load_list_setting(settings, name):
    """
    Sometimes users accidentally change settings that should be lists to
    just individual strings. This helps fix that.

    :param settings:
        A sublime.Settings object

    :param name:
        The name of the setting

    :return:
        The current value of the setting, always a set
    """

    value = settings.get(name)
    if not value:
        return set()
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return set()

    return set(filter(lambda v: isinstance(v, str), value))


def save_list_setting(settings, filename, name, new_value, old_value=None):
    """
    Updates a list-valued setting

    :param settings:
        The sublime.Settings object

    :param filename:
        The settings filename to save in

    :param name:
        The setting name

    :param new_value:
        The new value for the setting

    :param old_value:
        If not None, then this and the new_value will be compared. If they
        are the same, the settings will not be flushed to disk.

    :return:
        ``True``, if settings have been saved.
        ``False``, if ``new_value`` and ``old_value`` were equal.
    """

    if not isinstance(old_value, set):
        new_value = set(new_value)

    if old_value is not None:
        if not isinstance(old_value, set):
            old_value = set(old_value)
        if old_value == new_value:
            return False

    settings.set(name, sorted(new_value, key=lambda s: s.lower()))
    sublime.save_settings(filename)
    return True
