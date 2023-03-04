import sublime
import sublime_plugin

from .. import text
from ..settings import pc_settings_filename
from ..show_error import show_message


class RemoveChannelCommand(sublime_plugin.ApplicationCommand):

    """
    A command to remove a channel from the user's Package Control settings

    Example:

    ```py
    sublime.run_command(
        "remove_channel",
        {
            "url": "https://my-server.com/channel.json",
            "unattended": False  # if True, suppress error dialogs
        }
    )
    ```
    """

    def run(self, url=None, unattended=False):
        settings = sublime.load_settings(pc_settings_filename())
        channels = settings.get('channels')
        if not channels:
            if not url or not unattended:
                show_message('There are no channels to remove')
            return

        if url:
            try:
                channels.remove(url)
            except (ValueError):
                pass
            else:
                settings.set('channels', channels)
                sublime.save_settings(pc_settings_filename())
                sublime.status_message('Channel %s successfully removed' % url)
            return

        if len(channels) == 1:
            message = text.format(
                '''
                Package Control

                You are about to remove the only channel in your settings. This
                will mean you will no longer be able to install or update
                packages.
                '''
            )
            if not sublime.ok_cancel_dialog(message, 'Ok'):
                return

        def on_done(index):
            if index == -1:
                return

            self.run(channels[index])

        sublime.active_window().show_quick_panel(
            channels,
            on_done,
            sublime.KEEP_OPEN_ON_FOCUS_LOST
        )
