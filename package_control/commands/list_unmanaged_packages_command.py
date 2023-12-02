import sublime

from ..settings import load_list_setting, pc_settings_filename
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
        ignored_packages = load_list_setting(settings, 'unmanaged_packages_ignore')
        ignored_packages |= load_list_setting(settings, 'installed_packages')

        packages = manager.list_packages() - ignored_packages
        return sorted(packages, key=lambda s: s.lower())
