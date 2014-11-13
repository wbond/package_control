import re

import sublime
import sublime_plugin

from ..show_error import show_error
from ..settings import pc_settings_filename


class AddChannelCommand(sublime_plugin.WindowCommand):
    """
    A command to add a new channel (list of repositories) to the user's machine
    """

    def run(self):
        self.window.show_input_panel('Channel JSON URL', '',
            self.on_done, self.on_change, self.on_cancel)

    def on_done(self, input):
        """
        Input panel handler - adds the provided URL as a channel

        :param input:
            A string of the URL to the new channel
        """

        input = input.strip()

        if re.match('https?://', input, re.I) == None:
            show_error(u"Unable to add the channel \"%s\" since it does not appear to be served via HTTP (http:// or https://)." % input)
            return

        settings = sublime.load_settings(pc_settings_filename())
        channels = settings.get('channels', [])
        if not channels:
            channels = []
        channels.append(input)
        settings.set('channels', channels)
        sublime.save_settings(pc_settings_filename())
        sublime.status_message(('Channel %s successfully ' +
            'added') % input)

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass
