import threading
import time

from ..package_disabler import PackageDisabler
from ..thread_progress import ThreadProgress
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
        Build a list of packages to display.

        :param manager:
            The package manager instance to use.

        :returns:
            A list of package names to add to the quick panel
        """

        return manager.list_packages()

    def on_done(self, manager, package_name):
        """
        Callback function to perform action on selected package.

        :param manager:
            The package manager instance to use.

        :param package_name:
            A package name to perform action for
        """

        thread = RemovePackageThread(manager, package_name)
        thread.start()
        ThreadProgress(
            thread,
            'Removing package %s' % package_name,
            'Package %s successfully removed' % package_name
        )


class RemovePackageThread(threading.Thread, PackageDisabler):

    """
    A thread to run the remove package operation in so that the Sublime Text
    UI does not become frozen
    """

    def __init__(self, manager, package):
        self.manager = manager
        self.package = package
        self.result = None
        threading.Thread.__init__(self)

    def run(self):
        self.disable_packages(self.package, 'remove')

        try:
            # Let the package disabling take place
            time.sleep(0.7)
            self.result = self.manager.remove_package(self.package)
        finally:
            # Do not reenable if removing deferred until next restart
            if self.result is not None:
                time.sleep(0.7)
                self.reenable_packages(self.package, 'remove')
