import threading
import time

import sublime
import sublime_plugin

from ..activity_indicator import ActivityIndicator
from ..console_write import console_write
from ..package_installer import PackageInstaller, USE_QUICK_PANEL_ITEM
from ..package_renamer import PackageRenamer
from ..show_error import show_error, show_message


class UpgradePackagesCommand(sublime_plugin.ApplicationCommand):

    """
    A command that accepts a list of packages to upgrade,
    or prompts the user to paste a comma-separated list.

    Example:

    ```py
    sublime.run_command(
        "upgrade_packages",
        {
            "packages": ["Package 1", "Package 2"],
            "unattended": False  # if True, suppress error dialogs
        }
    )
    ```
    """

    def run(self, packages=None, unattended=False):
        if isinstance(packages, list):
            UpgradePackagesThread(packages, unattended).start()
            return

        def on_done(input_text):
            packages = []
            for package in input_text.split(','):
                if package:
                    package = package.strip()
                    if package:
                        packages.append(package)

            if not packages:
                show_error('No package names were entered')
                return

            self.run(packages, False)

        sublime.active_window().show_input_panel(
            'Packages to upgrade (comma-separated)',
            '',
            on_done,
            None,
            None
        )


class UpgradePackagesThread(threading.Thread, PackageInstaller):

    """
    A thread to run the installation of one or more packages in
    """

    def __init__(self, packages, unattended):
        """
        Constructs a new instance.

        :param packages:
            The list of package names to upgrade.
            If `None` all packages are upgraded.

        :param unattended:
            A flag to decide whether to display modal error/message dialogs.
        """

        self.packages = set(packages) if packages else None
        self.unattended = unattended

        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        message = 'Loading repository...'
        with ActivityIndicator(message) as progress:
            console_write(message)

            PackageRenamer().rename_packages(self.manager)

            package_list = self.make_package_list(actions=(self.PULL, self.UPGRADE))

            if USE_QUICK_PANEL_ITEM:
                package_names = {
                    info.trigger for info in package_list
                    if self.packages is None or info.trigger in self.packages
                }
            else:
                package_names = {
                    info[0] for info in package_list
                    if self.packages is None or info[0] in self.packages
                }

            if not package_names:
                message = 'All specified packages up-to-date!'
                console_write(message)
                progress.finish(message)
                if not self.unattended:
                    show_message(message)
                return

            # If Package Control is being upgraded, just do that
            if 'Package Control' in package_names:
                package_names = {'Package Control'}

            num_packages = len(package_names)
            if num_packages > 1:
                console_write('Upgrading %d packages...' % num_packages)

            disabled_packages = self.disable_packages({self.UPGRADE: package_names})
            time.sleep(0.7)

            num_upgraded = 0

            try:
                for package in sorted(package_names, key=lambda s: s.lower()):
                    progress.set_label('Upgrading package %s' % package)
                    result = self.manager.install_package(package)
                    if result is True:
                        num_upgraded += 1
                    # do not re-enable package if operation is dereffered to next start
                    elif result is None and package in disabled_packages:
                        disabled_packages.remove(package)

                if num_packages == 1:
                    message = 'Package %s successfully upgraded' % list(package_names)[0]
                elif num_packages == num_upgraded:
                    message = 'All packages successfully upgraded'
                    console_write(message)
                else:
                    message = '%d of %d packages successfully upgraded' % (num_upgraded, num_packages)
                    console_write(message)

                progress.finish(message)

            finally:
                time.sleep(0.7)
                self.reenable_packages({self.UPGRADE: disabled_packages})
