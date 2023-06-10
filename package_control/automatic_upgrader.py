import os
import json
import datetime
# To prevent import errors in thread with datetime
import locale  # noqa
import time

import sublime

from . import sys_path
from .activity_indicator import ActivityIndicator
from .console_write import console_write
from .package_tasks import PackageTaskRunner


class AutomaticUpgrader:

    """
    Automatically checks for updated packages and installs them. controlled
    by the `auto_upgrade`, `auto_upgrade_ignore`, and `auto_upgrade_frequency`
    settings.
    """

    def __init__(self, manager):
        self.manager = manager
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

        frequency = self.manager.settings.get('auto_upgrade_frequency')
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
        Upgrades all packages that are not currently upgraded to the latest
        version. Also renames any installed packages to their new names.
        """

        upgrader = PackageTaskRunner(self.manager)

        with ActivityIndicator('Searching updates...') as progress:
            # upgrade existing libraries
            required_libraries = upgrader.manager.find_required_libraries()
            missing_libraries = upgrader.manager.find_missing_libraries(required_libraries=required_libraries)
            upgrader.manager.install_libraries(
                libraries=required_libraries - missing_libraries,
                fail_early=False
            )

            # run updater synchronously to delay any "You must restart ST" dialogues
            # Note: we are in PackageCleanup thread here
            completed = upgrader.upgrade_packages(
                ignore_packages=upgrader.manager.settings.get('auto_upgrade_ignore'),
                unattended=True,
                progress=progress
            )
            if completed:
                self.save_last_run()
