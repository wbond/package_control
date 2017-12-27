import re
import threading

import sublime_plugin

from ..package_installer import PackageInstaller
from ..show_error import show_error
from ..thread_progress import ThreadProgress


class AdvancedInstallPackageCommand(sublime_plugin.WindowCommand):

    """
    A command that accepts a comma-separated list of packages to install, or
    prompts the user to paste a comma-separated list
    """

    def run(self, packages=None):

        if packages:
            if isinstance(packages, str):
                packages = re.split(r'\s*,\s*', packages)

            if isinstance(packages, list):
                return self.start(packages)

        self.window.show_input_panel(
            'Packages to Install (Comma-separated)',
            '',
            self.on_done,
            None,
            None
        )

    def on_done(self, text):
        """
        Input panel handler - adds the provided URL as a repository

        :param text:
            A string of the URL to the new repository
        """

        text = text.strip()

        if not text:
            show_error(
                '''
                No package names were entered
                '''
            )
            return

        self.start(re.split(r'\s*,\s*', text))

    def start(self, packages):
        thread = AdvancedInstallPackageThread(packages)
        thread.start()
        message = 'Installing package'
        if len(packages) > 1:
            message += 's'
        ThreadProgress(thread, message, '')


class AdvancedInstallPackageThread(threading.Thread, PackageInstaller):

    """
    A thread to run the installation of one or more packages in
    """

    def __init__(self, packages):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the available package list in.
        """

        self.packages = packages
        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        installed = self.manager.list_packages()

        packages_to_install = [p for p in self.packages if p not in installed]
        packages_to_upgrade = [p for p in self.packages if p in installed]

        disabled_for_install = self.disable_packages(packages_to_install, 'install')
        disabled_for_upgrade = self.disable_packages(packages_to_upgrade, 'upgrade')

        # wait with installing the first package
        pause = True

        for package in packages_to_install:
            self.install(package, disabled_for_install, pause)
            pause = False

        for package in packages_to_upgrade:
            self.upgrade(package, disabled_for_upgrade, False)
