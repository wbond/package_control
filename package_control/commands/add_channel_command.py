import re

import sublime
import sublime_plugin

from ..settings import pc_settings_filename
from ..show_error import show_error


class AddChannelCommand(sublime_plugin.ApplicationCommand):

    """
    A command to add a new channel (list of repositories) to the user's machine
    """

    def run(self):
        sublime.active_window().show_input_panel('Channel JSON URL', '', self.on_done, self.on_change, self.on_cancel)

    def on_done(self, input_text):
        """
        Input panel handler - adds the provided URL as a channel

        :param input_text:
            A string of the URL to the new channel
        """

        input_text = input_text.strip()

        if re.match(r'https?://', input_text, re.I) is None:
            show_error(
                '''
                Unable to add the channel "%s" since it does not appear to be
                served via HTTP (http:// or https://).
                ''',
                input_text
            )
            return

        settings = sublime.load_settings(pc_settings_filename())
        channels = settings.get('channels', [])
        if not channels:
            channels = []
        channels.append(input_text)
        settings.set('channels', channels)
        sublime.save_settings(pc_settings_filename())
        sublime.status_message(('Channel %s successfully added') % input_text)

    def on_change(self, input_text):
        pass

    def on_cancel(self):
        pass
