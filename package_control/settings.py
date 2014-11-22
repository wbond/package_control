import sublime

try:
    str_cls = unicode
except (NameError):
    str_cls = str


def preferences_filename():
    """
    :return: The appropriate settings filename based on the version of Sublime Text
    """

    if int(sublime.version()) >= 2174:
        return 'Preferences.sublime-settings'
    return 'Global.sublime-settings'


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
        The current value of the setting, always a list
    """

    value = settings.get(name)
    if not value:
        value = []
    if isinstance(value, str_cls):
        value = [value]
    return value


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
    """

    # Clean up the list to only include unique values, sorted
    new_value = list(set(new_value))
    new_value = sorted(new_value, key=lambda s: s.lower())

    if old_value is not None:
        if old_value == new_value:
            return

    settings.set(name, new_value)
    sublime.save_settings(filename)
