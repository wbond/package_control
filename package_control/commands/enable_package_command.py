import sublime

from .. import text
from ..package_disabler import PackageDisabler
from .existing_packages_command import ExistingPackagesCommand


class EnablePackageCommand(ExistingPackagesCommand):

    """
    A command that removes a package from Sublime Text's ignored packages list
    """

    def action(self):
        """
        Build a strng to describe the action taken on selected package.
        """

        return "enable"

    def no_packages_error(self):
        """
        Return the error message to display if no packages are availablw.
        """

        return "There are no disabled packages to enable"

    def list_packages(self, manager):
        """
        Build a list of packages to display.

        :param manager:
            The package manager instance to use.

        :returns:
            A list of package names to add to the quick panel
        """

        return sorted(PackageDisabler.get_ignored_packages(), key=lambda s: s.lower())

    def on_done(self, manager, package_name):
        """
        Quick panel user selection handler - enables the selected package

        :param manager:
            The package manager instance to use.

        :param package_name:
            A package name to perform action for
        """

        PackageDisabler.reenable_packages(package_name, 'enable')

        sublime.status_message(text.format(
            '''
            Package %s successfully removed from list of disabled packages -
            restarting Sublime Text may be required
            ''',
            package_name
        ))
