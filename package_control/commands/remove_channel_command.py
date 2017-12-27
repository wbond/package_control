import sublime
import sublime_plugin

from .. import text
from ..settings import pc_settings_filename
from ..show_error import show_message
from ..show_quick_panel import show_quick_panel


class RemoveChannelCommand(sublime_plugin.WindowCommand):

    """
    A command to remove a channel from the user's Package Control settings
    """

    def __init__(self, window):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the list of installed packages in.
        """

        sublime_plugin.WindowCommand.__init__(self, window)
        self.channels = None
        self.settings = None

    def run(self):
        self.settings = sublime.load_settings(pc_settings_filename())
        self.channels = self.settings.get('channels')

        if not self.channels:
            show_message('There are no channels to remove')
            return

        if len(self.channels) == 1:
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

        show_quick_panel(self.window, self.channels, self.on_done)

    def on_done(self, index):
        """
        Quick panel handler - removes the channel from settings

        :param index:
            The numeric index of the channel in the list of channels
        """

        # Cancelled
        if index == -1:
            return

        channel = self.channels[index]

        try:
            self.channels.remove(channel)
            self.settings.set('channels', self.channels)
            sublime.save_settings(pc_settings_filename())
            sublime.status_message('Channel %s successfully removed' % channel)

        except (ValueError):
            pass
