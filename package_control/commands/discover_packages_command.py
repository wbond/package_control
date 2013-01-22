import sublime_plugin


class DiscoverPackagesCommand(sublime_plugin.WindowCommand):
    """
    A command that opens the community package list webpage
    """

    def run(self):
        self.window.run_command('open_url',
            {'url': 'http://wbond.net/sublime_packages/community'})
