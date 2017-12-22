import re

import sublime
import sublime_plugin

from ..settings import load_list_setting
from ..settings import pc_settings_filename
from ..show_error import show_error


class AddChannelCommand(sublime_plugin.WindowCommand):

    """
    A command to add a new channel (list of repositories) to the user's machine
    """

    def run(self):
        self.window.show_input_panel(
            'Channel JSON URL',
            '',
            self.on_done,
            None,
            None
        )

    def on_done(self, text):
        """
        Input panel handler - adds the provided URL as a channel

        :param text:
            A string of the URL to the new channel
        """

        text = text.strip()

        if re.match('https?://', text, re.I) is None:
            show_error(
                '''
                Unable to add the channel "%s" since it does not appear to be
                served via HTTP (http:// or https://).
                ''',
                text
            )
            return

        settings = sublime.load_settings(pc_settings_filename())
        channels = load_list_setting(settings, 'channels')
        channels.append(text)
        settings.set('channels', channels)
        sublime.save_settings(pc_settings_filename())
        sublime.status_message('Channel %s successfully added' % text)
