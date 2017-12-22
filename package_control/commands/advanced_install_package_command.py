import functools
import re
import threading
import time

import sublime
import sublime_plugin

from ..package_disabler import PackageDisabler
from ..package_manager import PackageManager
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


class AdvancedInstallPackageThread(threading.Thread, PackageDisabler):

    """
    A thread to run the installation of one or more packages in
    """

    def __init__(self, packages):
        """
        :param window:
            An instance of :class:`sublime.Window` that represents the Sublime
            Text window to show the available package list in.
        """

        self.manager = PackageManager()
        self.packages = packages

        self.installed = self.manager.list_packages()
        self.disabled = []
        for package_name in packages:
            operation_type = 'install' if package_name not in self.installed else 'upgrade'
            self.disabled.extend(self.disable_packages(package_name, operation_type))

        threading.Thread.__init__(self)

    def run(self):
        # Allow packages to properly disable
        time.sleep(0.7)

        def do_reenable_package(package_name):
            operation_type = 'install' if package_name not in self.installed else 'upgrade'
            self.reenable_package(package_name, operation_type)

        for package in self.packages:
            result = self.manager.install_package(package)

            # Do not reenable if installation deferred until next restart
            if result is not None and package in self.disabled:
                # We use a functools.partial to generate the on-complete callback in
                # order to bind the current value of the parameters, unlike lambdas.
                sublime.set_timeout(functools.partial(do_reenable_package, package), 700)
