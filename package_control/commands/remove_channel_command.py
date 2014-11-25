import sublime
import sublime_plugin

from ..show_error import show_error
from ..settings import pc_settings_filename


class RemoveChannelCommand(sublime_plugin.WindowCommand):
    """
    A command to remove a channel from the user's Package Control settings
    """

    def run(self):
        self.settings = sublime.load_settings(pc_settings_filename())
        self.channels = self.settings.get('channels')
        if not self.channels:
            show_error(u'There are no channels to remove.')
            return

        run = False
        if len(self.channels) == 1:
            message = u"Package Control\n\nYou are about to remove the " + \
                u"only channel in your settings. This will mean you will " + \
                u"no longer be able to install or update packages."
            if sublime.ok_cancel_dialog(message, 'Ok'):
                run = True
        else:
            run = True

        if run:
            self.window.show_quick_panel(self.channels, self.on_done)

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
