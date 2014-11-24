import time
import threading

import sublime
import sublime_plugin

from ..thread_progress import ThreadProgress
from ..package_installer import PackageInstaller, PackageInstallerThread
from ..package_renamer import PackageRenamer


class UpgradeAllPackagesCommand(sublime_plugin.WindowCommand):
    """
    A command to automatically upgrade all installed packages that are
    upgradable.
    """

    def run(self):
        package_renamer = PackageRenamer()
        package_renamer.load_settings()

        thread = UpgradeAllPackagesThread(self.window, package_renamer)
        thread.start()
        ThreadProgress(thread, 'Loading repositories', '')


class UpgradeAllPackagesThread(threading.Thread, PackageInstaller):
    """
    A thread to run the action of retrieving upgradable packages in.
    """

    def __init__(self, window, package_renamer):
        self.window = window
        self.package_renamer = package_renamer
        self.completion_type = 'upgraded'
        threading.Thread.__init__(self)
        PackageInstaller.__init__(self)

    def run(self):
        self.package_renamer.rename_packages(self)
        package_list = self.make_package_list(['install', 'reinstall', 'none'])

        disabled_packages = []

        def do_upgrades():
            # Pause so packages can be disabled
            time.sleep(0.7)

            # We use a function to generate the on-complete lambda because if
            # we don't, the lambda will bind to info at the current scope, and
            # thus use the last value of info from the loop
            def make_on_complete(name):
                return lambda: self.reenable_package(name)

            for info in package_list:
                if info[0] in disabled_packages:
                    on_complete = make_on_complete(info[0])
                else:
                    on_complete = None
                thread = PackageInstallerThread(self.manager, info[0],
                    on_complete)
                thread.start()
                ThreadProgress(thread, 'Upgrading package %s' % info[0],
                    'Package %s successfully %s' % (info[0],
                    self.completion_type))
                thread.join()

        # Disabling a package means changing settings, which can only be done
        # in the main thread. We then create a new background thread so that
        # the upgrade process does not block the UI.
        def disable_packages():
            package_names = []
            for info in package_list:
                package_names.append(info[0])
            disabled_packages.extend(self.disable_packages(package_names, 'upgrade'))
            threading.Thread(target=do_upgrades).start()

        sublime.set_timeout(disable_packages, 1)
