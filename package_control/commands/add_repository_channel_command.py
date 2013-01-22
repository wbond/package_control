import sublime
import sublime_plugin


class AddRepositoryChannelCommand(sublime_plugin.WindowCommand):
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

        settings = sublime.load_settings('Package Control.sublime-settings')
        repository_channels = settings.get('repository_channels', [])
        if not repository_channels:
            repository_channels = []
        repository_channels.append(input)
        settings.set('repository_channels', repository_channels)
        sublime.save_settings('Package Control.sublime-settings')
        sublime.status_message(('Channel %s successfully ' +
            'added') % input)

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass
