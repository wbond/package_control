import os
import json
import datetime
# To prevent import errors in thread with datetime
import locale  # noqa
import time

import sublime

from . import sys_path
from .console_write import console_write
from .package_installer import PackageInstaller
from .package_renamer import PackageRenamer
from .settings import pc_settings_filename

USE_QUICK_PANEL_ITEM = hasattr(sublime, 'QuickPanelItem')


class AutomaticUpgrader:

    """
    Automatically checks for updated packages and installs them. controlled
    by the `auto_upgrade`, `auto_upgrade_ignore`, and `auto_upgrade_frequency`
    settings.
    """

    def __init__(self):
        self.settings = sublime.load_settings(pc_settings_filename())
        self.last_run = 0
        self.last_version = 0
        self.next_run = 0
        self.current_version = int(sublime.version())

    def run(self):
        self.load_last_run()

        if self.last_version != self.current_version and self.last_version != 0:
            console_write(
                '''
                Detected Sublime Text update, looking for package updates
                '''
            )

        elif self.next_run > int(time.time()):
            last_run = datetime.datetime.fromtimestamp(self.last_run)
            next_run = datetime.datetime.fromtimestamp(self.next_run)
            date_format = '%Y-%m-%d %H:%M:%S'
            console_write(
                '''
                Skipping automatic upgrade, last run at %s, next run at %s or after
                ''',
                (last_run.strftime(date_format), next_run.strftime(date_format))
            )
            return

        self.upgrade_packages()

    def load_last_run(self):
        """
        Loads the last run time from disk into memory
        """

        try:
            with open(os.path.join(sys_path.pc_cache_dir(), 'last_run.json')) as fobj:
                last_run_data = json.load(fobj)
            self.last_run = int(last_run_data['timestamp'])
            self.last_version = int(last_run_data['st_version'])
        except (FileNotFoundError, ValueError, TypeError):
            pass

        frequency = self.settings.get('auto_upgrade_frequency')
        if frequency and self.last_run:
            self.next_run = int(self.last_run) + (frequency * 60 * 60)

    def save_last_run(self):
        """
        Saves a record of when the last run was
        """

        with open(os.path.join(sys_path.pc_cache_dir(), 'last_run.json'), 'w') as fobj:
            json.dump({
                'timestamp': int(time.time()),
                'st_version': self.current_version
            }, fp=fobj)

    def upgrade_packages(self):
        """
        Upgrades all packages that are not currently upgraded to the lastest
        version. Also renames any installed packages to their new names.
        """

        installer = PackageInstaller()

        required_libraries = installer.manager.find_required_libraries()
        missing_libraries = installer.manager.find_missing_libraries(required_libraries=required_libraries)
        installer.manager.install_libraries(
            libraries=required_libraries - missing_libraries,
            fail_early=False
        )

        PackageRenamer().rename_packages(installer.manager)

        package_list = installer.make_package_list(
            [
                'install',
                'reinstall',
                'downgrade',
                'overwrite',
                'none'
            ],
            ignore_packages=self.settings.get('auto_upgrade_ignore')
        )
        if not package_list:
            self.save_last_run()
            console_write('All packages up-to-date!')
            return

        if USE_QUICK_PANEL_ITEM:
            package_list = [info.trigger for info in package_list]
        else:
            package_list = [info[0] for info in package_list]

        # If Package Control is being upgraded, just do that and restart
        if 'Package Control' in package_list:
            package_list = ['Package Control']
        else:
            self.save_last_run()

        console_write(
            'Upgrading %d package%s...',
            (len(package_list), 's' if len(package_list) != 1 else '')
        )

        reenable_packages = installer.disable_packages(package_list, 'upgrade')
        # Wait so that the ignored packages can be "unloaded"
        time.sleep(0.7)

        try:
            for package_name in package_list:
                result = installer.manager.install_package(package_name)

                # re-enable if upgrade is not deferred to next start
                if result is None and package_name in reenable_packages:
                    reenable_packages.remove(package_name)

        finally:
            if reenable_packages:
                time.sleep(0.7)
                installer.reenable_packages(reenable_packages, 'upgrade')
