import re

import sublime
import sublime_plugin

from ..console_write import console_write
from ..settings import pc_settings_filename
from ..show_error import show_error


class AddChannelCommand(sublime_plugin.ApplicationCommand):

    """
    A command to add a new channel (list of repositories) to the user's machine

    Example:

    ```py
    sublime.run_command(
        "add_channel",
        {
            "url": "https://my-server.com/channel.json",
            "unattended": False  # if True, suppress error dialogs
        }
    )
    ```
    """

    def run(self, url=None, unattended=False):
        if isinstance(url, str):
            url = url.strip()

            if re.match(r'^(?:file:///|https?://)', url, re.I) is None:
                output_fn = console_write if unattended else show_error
                output_fn(
                    '''
                    Unable to add the channel "%s" since it does not appear to be
                    served via HTTP (http:// or https://).
                    ''',
                    url
                )
                return

            settings = sublime.load_settings(pc_settings_filename())
            channels = settings.get('channels')
            if not channels:
                channels = []
            elif url in channels:
                return
            channels.append(url)
            settings.set('channels', channels)
            sublime.save_settings(pc_settings_filename())
            sublime.status_message('Channel %s successfully added' % url)
            return

        sublime.active_window().show_input_panel(
            'Channel JSON URL',
            '',
            self.run,
            None,
            None
        )
