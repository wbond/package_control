import sublime

from ..settings import pc_settings_filename, load_list_setting
from .list_packages_command import ListPackagesCommand


class ListUnmanagedPackagesCommand(ListPackagesCommand):

    """
    A command that shows a list of all packages that are not managed by
    Package Control, i.e. that are installed, but not mentioned in
    `installed_packages`.
    """

    def list_packages(self, manager):
        """
        Build a list of packages to display.

        :param manager:
            The package manager instance to use.

        :returns:
            A list of package names to add to the quick panel
        """

        settings = sublime.load_settings(pc_settings_filename())
        ignored_packages = set(load_list_setting(settings, 'unmanaged_packages_ignore'))
        ignored_packages |= set(load_list_setting(settings, 'installed_packages'))

        return sorted(set(manager.list_packages()) - ignored_packages, key=lambda s: s.lower())
