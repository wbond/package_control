import sublime_plugin


class DiscoverPackagesCommand(sublime_plugin.WindowCommand):
    """
    A command that opens the Package Control website
    """

    def run(self):
        self.window.run_command('open_url',
            {'url': 'https://packagecontrol.io/#discover'})
