import sublime

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

        return sorted(
            filter(lambda p: manager.is_compatible(p), PackageDisabler.ignored_packages()),
            key=lambda s: s.lower()
        )

    def on_done(self, manager, package_name):
        """
        Quick panel user selection handler - enables the selected package

        :param manager:
            The package manager instance to use.

        :param package_name:
            A package name to perform action for
        """

        PackageDisabler.reenable_packages({PackageDisabler.ENABLE: package_name})

        sublime.status_message('Package %s successfully enabled.' % package_name)
