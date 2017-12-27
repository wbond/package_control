import sublime
import sublime_plugin

from ..settings import load_list_setting
from ..settings import pc_settings_filename
from .list_packages_command import ListPackagesThread


class ListUnmanagedPackagesCommand(sublime_plugin.WindowCommand):

    """
    A command that shows a list of all packages that are not managed by
    Package Control, i.e. that are installed, but not mentioned in
    `installed_packages`.
    """

    def run(self):
        settings = sublime.load_settings(pc_settings_filename())

        ignored_packages = load_list_setting(settings, 'unmanaged_packages_ignore')
        ignored_packages.extend(load_list_setting(settings, 'installed_packages'))

        def filter_packages(package):
            return package[0] not in ignored_packages

        ListPackagesThread(self.window, filter_packages).start()
