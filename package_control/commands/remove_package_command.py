import threading

from ..activity_indicator import ActivityIndicator
from ..package_tasks import PackageTaskRunner
from .existing_packages_command import ExistingPackagesCommand


class RemovePackageCommand(ExistingPackagesCommand):

    """
    A command that presents a list of installed packages, allowing the user to
    select one to remove
    """

    def action(self):
        """
        Build a strng to describe the action taken on selected package.
        """

        return "remove"

    def no_packages_error(self):
        """
        Return the error message to display if no packages are availablw.
        """

        return "There are no packages that can be removed"

    def list_packages(self, manager):
        """
        Build a list of packages installed by user.

        :param manager:
            The package manager instance to use.

        :returns:
            A list of package names to add to the quick panel
        """

        return manager.list_packages() - manager.cooperate_packages()

    def on_done(self, manager, package_name):
        """
        Callback function to perform action on selected package.

        :param manager:
            The package manager instance to use.

        :param package_name:
            A package name to perform action for
        """

        def worker():
            with ActivityIndicator() as progress:
                remover = PackageTaskRunner(manager)
                remover.remove_packages({package_name}, progress)

        threading.Thread(target=worker).start()
