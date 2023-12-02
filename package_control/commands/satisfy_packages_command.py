import threading

import sublime_plugin

from ..activity_indicator import ActivityIndicator
from ..package_tasks import PackageTaskRunner


class SatisfyPackagesCommand(sublime_plugin.ApplicationCommand):

    """
    A command to sync ``installed_packages`` with filesystem.

    It installs missing packages, which are listed in ``installed_packages``
    but are not present on filesystem.

    It removes managed packages, which are found on filesystem but are not
    present in ``installed_packages``.
    """

    def run(self):

        def worker():
            message = 'Satisfying packages...'
            with ActivityIndicator(message) as progress:
                installer = PackageTaskRunner()
                installer.satisfy_packages(progress)

        threading.Thread(target=worker).start()
