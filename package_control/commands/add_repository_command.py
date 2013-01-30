import sublime
import sublime_plugin


class AddRepositoryCommand(sublime_plugin.WindowCommand):
    """
    A command to add a new repository to the user's machine
    """

    def run(self):
        self.window.show_input_panel('GitHub or BitBucket Web URL, or Custom' +
                ' JSON Repository URL', '', self.on_done,
            self.on_change, self.on_cancel)

    def on_done(self, input):
        """
        Input panel handler - adds the provided URL as a repository

        :param input:
            A string of the URL to the new repository
        """

        settings = sublime.load_settings('Package Control.sublime-settings')
        repositories = settings.get('repositories', [])
        if not repositories:
            repositories = []
        repositories.append(input)
        settings.set('repositories', repositories)
        sublime.save_settings('Package Control.sublime-settings')
        sublime.status_message('Repository %s successfully added' % input)

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass
