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
