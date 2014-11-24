import threading
import re
import time

import sublime
import sublime_plugin

from ..show_error import show_error
from ..package_manager import PackageManager
from ..package_disabler import PackageDisabler
from ..thread_progress import ThreadProgress

try:
    str_cls = unicode
    bytes_cls = str
except (NameError):
    str_cls = str
    bytes_cls = bytes


class AdvancedInstallPackageCommand(sublime_plugin.WindowCommand):
    """
    A command that accepts a comma-separated list of packages to install, or
    prompts the user to paste a comma-separated list
    """

    def run(self, packages=None):
        is_str   = isinstance(packages, str_cls)
        is_bytes = isinstance(packages, bytes_cls)

        if packages and (is_str or is_bytes):
            packages = self.split(packages)

        if packages and isinstance(packages, list):
            return self.start(packages)

        self.window.show_input_panel('Packages to Install (Comma-separated)',
            '', self.on_done, None, None)

    def split(self, packages):
        if isinstance(packages, bytes_cls):
            packages = package.decode('utf-8')
        return re.split(u'\s*,\s*', packages)

    def on_done(self, input):
        """
        Input panel handler - adds the provided URL as a repository

        :param input:
            A string of the URL to the new repository
        """

        input = input.strip()

        if not input:
            show_error(u"No package names were entered" % input)
            return

        self.start(self.split(input))

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

        self.disabled = self.disable_packages(packages, 'install')
        self.installed = self.manager.list_packages()

        threading.Thread.__init__(self)

    def run(self):
        # Allow packages to properly disable
        time.sleep(0.7)

        for package in self.packages:
            self.manager.install_package(package)

            # We use a wrapper function since this call is in a loop, so
            # directly using the "package" variable would cause the value to
            # change between when we set the callback and executed it.
            def reenable_package(package_name):
                def do_reenable_package():
                    type_ = 'install' if package_name not in self.installed else 'upgrade'
                    self.reenable_package(package_name, type_)
                return do_reenable_package
            sublime.set_timeout(reenable_package(package), 700)
