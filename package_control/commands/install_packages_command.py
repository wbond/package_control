import threading
import time

import sublime
import sublime_plugin

from ..activity_indicator import ActivityIndicator
from ..console_write import console_write
from ..package_installer import PackageInstaller, USE_QUICK_PANEL_ITEM
from ..show_error import show_error, show_message


class InstallPackagesCommand(sublime_plugin.ApplicationCommand):

    """
    A command that accepts a list of packages to install,
    or prompts the user to paste a comma-separated list.

    Example:

    ```py
    sublime.run_command(
        "install_packages",
        {
            "packages": ["Package 1", "Package 2"],
            "unattended": False  # don't suppress error dialogs
        }
    )
    ```
    """

    def run(self, packages=None, unattended=False):
        if isinstance(packages, list):
            InstallPackagesThread(packages, unattended).start()
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
            'Packages to install (comma-separated)',
            '',
            on_done,
            None,
            None
        )


class InstallPackagesThread(threading.Thread, PackageInstaller):

    """
    A thread to run the installation of one or more packages in
    """

    def __init__(self, packages, unattended):
        """
        Constructs a new instance.

        :param packages:
            The list of package names

        :param unattended:
            A flag to decide whether to display modal error/message dialogs.
        """

        self.packages = set(packages)
        self.unattended = unattended

        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        message = 'Loading repository...'
        with ActivityIndicator(message) as progress:
            console_write(message)
            package_list = self.make_package_list(actions=(self.INSTALL, self.OVERWRITE))
            if not package_list:
                message = 'There are no packages available for installation'
                console_write(message)
                progress.finish(message)
                if not self.unattended:
                    show_message(
                        '''
                        %s

                        Please see https://packagecontrol.io/docs/troubleshooting for help
                        ''',
                        message
                    )
                return

            if USE_QUICK_PANEL_ITEM:
                package_names = {info.trigger for info in package_list if info.trigger in self.packages}
            else:
                package_names = {info[0] for info in package_list if info[0] in self.packages}

            if not package_names:
                message = 'All specified packages already installed!'
                console_write(message)
                progress.finish(message)
                if not self.unattended:
                    show_message(message)
                return

            num_packages = len(package_names)
            if num_packages > 1:
                console_write('Installing %d packages...' % num_packages)

            self.disable_packages({self.INSTALL: package_names})
            time.sleep(0.7)

            deffered = set()
            num_installed = 0

            try:
                for package in sorted(package_names, key=lambda s: s.lower()):
                    progress.set_label('Installing package %s' % package)
                    result = self.manager.install_package(package)
                    if result is True:
                        num_installed += 1
                    # do not re-enable package if operation is dereffered to next start
                    elif result is None:
                        deffered.add(package)

                if num_packages == 1:
                    message = 'Package %s successfully installed' % list(package_names)[0]
                elif num_packages == num_installed:
                    message = 'All packages successfully installed'
                    console_write(message)
                else:
                    message = '%d of %d packages successfully installed' % (num_installed, num_packages)
                    console_write(message)

                progress.finish(message)

            finally:
                time.sleep(0.7)
                self.reenable_packages({self.INSTALL: package_names - deffered})
