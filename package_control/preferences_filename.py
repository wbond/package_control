import sublime


def preferences_filename():
    """
    :return: The appropriate settings filename based on the version of Sublime Text
    """

    if int(sublime.version()) >= 2174:
        return 'Preferences.sublime-settings'
    return 'Global.sublime-settings'


def pc_preferences_filename():
    """
    :return: The settings file for Package Control
    """

    return 'Package Control.sublime-settings'
