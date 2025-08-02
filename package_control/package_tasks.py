from datetime import datetime
import html
import re
import time

from concurrent import futures

import sublime

from .console_write import console_write
from .package_manager import PackageManager
from .package_disabler import PackageDisabler
from .package_version import PackageVersion
from .show_error import show_message

USE_QUICK_PANEL_ITEM = hasattr(sublime, 'QuickPanelItem')


class BasePackageTask:
    __slots__ = ['action', 'package_name']

    def __init__(self, action, name):
        self.action = action
        self.package_name = name

    def __repr__(self):
        return '{}({}, {})'.format(self.__class__.__name__, self.action, self.package_name)


class PackageInstallTask(BasePackageTask):
    __slots__ = ['package_version', 'update_info', 'upgrader']

    def __init__(self, action, name, version=None, update_info=None, upgrader=None):
        super().__init__(action, name)
        self.package_version = version
        self.update_info = update_info
        self.upgrader = upgrader

    @property
    def package_description(self):
        description = None
        if self.update_info:
            description = self.update_info.get('description')
        return description or 'No description provided'

    @property
    def package_homepage(self):
        if not self.update_info:
            return ""
        return self.update_info['homepage']

    @property
    def available_name(self):
        name = None
        if self.update_info:
            name = self.update_info['name']
        return name or self.package_name

    @property
    def available_release(self):
        if not self.update_info:
            return None
        return self.update_info['releases'][0]

    @property
    def available_version(self):
        if not self.available_release:
            return None
        return PackageVersion(self.available_release['version'])

    @property
    def last_modified(self):
        if not self.update_info:
            return None
        return self.update_info['last_modified']


class PackageTaskRunner(PackageDisabler):
    """
    Provides business logic related to installing/upgrading or removing packages
    """

    NONE = 'none'
    """
    Do nothing.
    """

    DOWNGRADE = 'downgrade'
    """
    Downgrade an installed package if latest available one is of smaller version.
    """

    REINSTALL = 'reinstall'
    """
    Reinstall existing managed packages.
    """

    OVERWRITE = 'overwrite'
    """
    Overwrite existing unmanaged packages.
    """

    PULL = 'pull'
    """
    Upgrade unmanaged vcs packages.
    """

    def __init__(self, manager=None):
        """
        Constructs a new instance.

        :param manager:
            An optional PackageManager object to re-use.
            If `None` or nothing is given, a new instance is created.
        """

        self.manager = manager or PackageManager()

    def install_packages(self, packages, unattended=False, progress=None):
        """
        Install specified packages

        :param packages:
            A list or set of unicode strings with package names to install.

        :param unattended:
            If ``True`` suppress message dialogs and don't focus "Package Control Messages".

        :param progress:
            An ``ActivityIndicator`` object to use for status information.
        """

        if packages is not None:
            if isinstance(packages, str):
                packages = {packages}
            elif not isinstance(packages, set):
                if not isinstance(packages, (list, tuple)):
                    raise TypeError("Argument 'packages' must be a string, list or set!")
                packages = set(packages)

        tasks = self.create_package_tasks(
            actions=(self.INSTALL, self.OVERWRITE),
            include_packages=packages
        )
        if tasks is False:
            message = 'There are no packages available for installation'
            console_write(message)
            if progress:
                progress.finish(message)
            if not unattended:
                show_message(
                    '''
                    %s

                    Please see https://packagecontrol.io/docs/troubleshooting for help
                    ''',
                    message
                )
            return

        if not tasks:
            message = 'All specified packages already installed!'
            console_write(message)
            if progress:
                progress.finish(message)
            if not unattended:
                show_message(message)
            return

        return self.run_install_tasks(tasks, progress, unattended)

    def upgrade_packages(self, packages=None, ignore_packages=None, unattended=False, progress=None):
        """
        Upgrade specified packages

        :param packages:
            A list or set of unicode strings with package names to upgrade.
            If ``None``, all outdated packages are updated.

        :param ignore_packages:
            A list or set of unicode strings with package names to exclude from updating.

        :param unattended:
            If ``True`` suppress message dialogs and don't focus "Package Control Messages".

        :param progress:
            An ``ActivityIndicator`` object to use for status information.

        :return:
            ``True``, if upgrade was completed.
            ``False``, if Package Control has been updated.
        """

        if packages is not None:
            if isinstance(packages, str):
                packages = {packages}
            elif not isinstance(packages, set):
                if not isinstance(packages, (list, tuple)):
                    raise TypeError("Argument 'packages' must be a string, list or set!")
                packages = set(packages)

        if ignore_packages is None:
            ignore_packages = set()
        elif isinstance(ignore_packages, str):
            ignore_packages = {ignore_packages}
        elif not isinstance(ignore_packages, set):
            if not isinstance(ignore_packages, (list, tuple)):
                raise TypeError("Argument 'ignore_packages' must be a string, list or set!")
            ignore_packages = set(ignore_packages)

        tasks = self.create_package_tasks(
            actions=(self.PULL, self.UPGRADE),
            include_packages=packages,
            ignore_packages=ignore_packages | self.ignored_packages()  # don't upgrade disabled packages
        )
        if tasks is False:
            message = 'There are no packages available for upgrade'
            console_write(message)
            if progress:
                progress.finish(message)
            if not unattended:
                show_message(
                    '''
                    %s

                    Please see https://packagecontrol.io/docs/troubleshooting for help
                    ''',
                    message
                )
            return True

        if not tasks:
            message = 'All specified packages up-to-date!'
            console_write(message)
            if progress:
                progress.finish(message)
            if not unattended:
                show_message(message)
            return True

        return self.run_upgrade_tasks(tasks, progress, unattended)

    def remove_packages(self, packages, progress=None, package_kind=''):
        """
        Removes packages.

        :param packages:
            A list or set of unicode strings with package names to remove.

        :param progress:
            An ``ActivityIndicator`` object to use for status information.

        :param package_kind:
            A unicode string with an additional package attribute.
            (e.g.: `orphaned`, `incompatible`, ...)
        """

        if package_kind:
            package_kind += ' '

        if isinstance(packages, str):
            packages = {packages}
        elif not isinstance(packages, set):
            if not isinstance(packages, (list, tuple)):
                raise TypeError("Argument 'packages' must be a string, list or set!")
            packages = set(packages)

        # prevent predefined packages from being removed
        packages -= self.manager.predefined_packages()

        num_packages = len(packages)
        if num_packages == 1:
            message = 'Removing {}package {}'.format(package_kind, list(packages)[0])
        else:
            message = 'Removing {} {}packages...'.format(num_packages, package_kind)
            console_write(message)

        if progress:
            progress.set_label(message)

        self.disable_packages({self.REMOVE: packages})
        time.sleep(0.7)

        deferred = set()
        num_success = 0

        try:
            for package in sorted(packages, key=lambda s: s.lower()):
                if progress:
                    progress.set_label('Removing {}package {}'.format(package_kind, package))
                result = self.manager.remove_package(package)
                if result is True:
                    num_success += 1
                # do not re-enable package if operation is deferred to next start
                elif result is None:
                    deferred.add(package)

            required_libraries = self.manager.find_required_libraries()
            self.manager.cleanup_libraries(required_libraries=required_libraries)

            if num_packages == 1:
                message = 'Package {} successfully removed'.format(list(packages)[0])
            elif num_packages == num_success:
                message = 'All {}packages successfully removed'.format(package_kind)
                console_write(message)
            else:
                message = '{} of {} {}packages successfully removed'.format(
                    num_success, num_packages, package_kind)
                console_write(message)

            if progress:
                progress.finish(message)

        finally:
            time.sleep(0.7)
            self.reenable_packages({self.REMOVE: packages - deferred})

    def satisfy_packages(self, progress=None, unattended=False):
        """
        Install missing and remove orphaned packages.

        :param progress:
            An ``ActivityIndicator`` object to use for status information.

        :param unattended:
            If ``True`` suppress message dialogs and don't focus "Package Control Messages".
        """

        installed_packages = self.manager.installed_packages()
        found_packages = self.manager.list_packages()

        # find missing packages
        tasks = self.create_package_tasks(
            actions=(self.INSTALL, self.OVERWRITE),
            include_packages=installed_packages,
            found_packages=found_packages
        )

        if tasks:
            self.run_install_tasks(tasks, progress, unattended, package_kind='missing')

        # find all managed orphaned packages
        orphaned_packages = set(filter(self.manager.is_managed, found_packages - installed_packages))
        if orphaned_packages:
            self.remove_packages(orphaned_packages, progress, package_kind='orphaned')

        message = 'All packages satisfied!'
        console_write(message)
        if progress:
            progress.finish(message)

    def run_install_tasks(self, tasks, progress=None, unattended=False, package_kind=''):
        """
        Execute specified package install tasks

        :param tasks:
            A list or set of ``PackageInstallTask`` objects.

        :param progress:
            An ``ActivityIndicator`` object to use for status information.

        :param unattended:
            If ``True`` suppress message dialogs and don't focus "Package Control Messages".

        :param package_kind:
            A unicode string with an additional package attribute.
            (e.g.: `missing`, ...)
        """

        if package_kind:
            package_kind += ' '

        num_packages = len(tasks)
        if num_packages == 1:
            message = 'Installing {}package {}'.format(package_kind, tasks[0].package_name)
        else:
            message = 'Installing {} {}packages...'.format(num_packages, package_kind)
            console_write(message)

        if progress:
            progress.set_label(message)

        package_names = set(task.package_name for task in tasks)

        self.disable_packages({self.INSTALL: package_names})
        time.sleep(0.7)

        num_success = 0

        try:
            for task in tasks:
                if progress:
                    progress.set_label('Installing {}package {}'.format(package_kind, task.package_name))
                result = self.manager.install_package(task.package_name, unattended)
                if result is True:
                    num_success += 1
                # do not re-enable package if operation is deferred to next start
                elif result is None:
                    package_names.remove(task.package_name)

            required_libraries = self.manager.find_required_libraries()
            self.manager.install_libraries(libraries=required_libraries, fail_early=False)
            self.manager.cleanup_libraries(required_libraries=required_libraries)

            if num_packages == num_success:
                if package_kind or num_packages > 1:
                    message = 'All {}packages successfully installed'.format(package_kind)
                else:
                    message = 'Package {} successfully installed'.format(tasks[0].package_name)
                console_write(message)
            else:
                message = (
                    '{} of {} {}packages successfully installed. '
                    'Restart Sublime Text to attempt to install the remaining ones.'
                    .format(num_success, num_packages, package_kind)
                )
                console_write(message)

            if progress:
                progress.finish(message)

        finally:
            time.sleep(0.7)
            self.reenable_packages({self.INSTALL: package_names})

    def run_upgrade_tasks(self, tasks, progress=None, unattended=False):
        """
        Execute specified package update tasks

        :param tasks:
            A list or set of ``PackageInstallTask`` objects.

        :param progress:
            An ``ActivityIndicator`` object to use for status information.

        :param unattended:
            If ``True`` suppress message dialogs and don't focus "Package Control Messages".

        :return:
            ``True``, if upgrade was completed.
            ``False``, if Package Control has been updated.
        """

        update_completed = True

        disable_packages = {
            self.INSTALL: set(),
            self.REMOVE: set(),
            self.UPGRADE: set(),
        }

        for task in tasks:
            name = task.package_name

            # If Package Control is being upgraded, just do that
            if name == 'Package Control':
                tasks = [task]
                disable_packages = {self.UPGRADE: [name]}
                update_completed = False
                break

            if name != task.available_name:
                # upgrade and rename package
                disable_packages[self.INSTALL].add(task.available_name)
                disable_packages[self.REMOVE].add(name)
            else:
                disable_packages[self.UPGRADE].add(name)

        num_packages = len(tasks)
        if num_packages == 1:
            message = 'Upgrading package {}'.format(tasks[0].package_name)
        else:
            message = 'Upgrading {} packages...'.format(num_packages)
            console_write(message)

        if progress:
            progress.set_label(message)

        self.disable_packages(disable_packages)
        time.sleep(0.7)

        num_success = 0

        try:
            for task in tasks:
                package = task.package_name
                if progress:
                    progress.set_label('Upgrading package {}'.format(task.package_name))
                result = self.manager.install_package(package, unattended)
                if result is True:
                    num_success += 1
                # do not re-enable package if operation is deferred to next start
                elif result is None:
                    disable_packages[self.REMOVE].remove(package)
                    if package != task.available_name:
                        disable_packages[self.INSTALL].remove(task.available_name)

            required_libraries = self.manager.find_required_libraries()
            self.manager.install_libraries(libraries=required_libraries, fail_early=False)
            self.manager.cleanup_libraries(required_libraries=required_libraries)

            if num_packages == num_success:
                if num_packages > 1:
                    message = 'All packages successfully upgraded'
                else:
                    message = 'Package {} successfully upgraded'.format(tasks[0].package_name)
                console_write(message)
            else:
                message = (
                    '{} of {} packages successfully upgraded. '
                    'Restart Sublime Text to attempt to upgrade the remaining ones.'
                    .format(num_success, num_packages)
                )
                console_write(message)

            if progress:
                progress.finish(message)

        finally:
            time.sleep(0.7)
            self.reenable_packages(disable_packages)

        return update_completed

    def create_package_tasks(self, actions, include_packages=None, ignore_packages=None, found_packages=None):
        """
        Makes tasks.

        :param actions:
            A list or tuple of actions to include packages by. Valid actions include:
            `install`, `upgrade`, `downgrade`, `reinstall`, `overwrite`,
            `pull` and `none`. `pull` and `none` are for Git and Hg repositories.
            `pull` is present when incoming changes are detected,
            where as `none` is selected if no commits are available. `overwrite`
            is for packages that do not include version information via the
            `package-metadata.json` file.

        :param include_packages:
            A list/set of package names to return tasks for.

        :param ignore_packages:
            A list/set of package names that should not be returned in the list

        :param found_packages:
            A list/set of package names found on filesystem to be used for task creation.
            It primarily exists to re-use existing data for optimization purposes.
            If ``None`` is provided, a list is created internally.

        :return:
            A list of ``PackageInstallTask`` objects on success.
            ``False``, if no packages are available upstream, most likely a connection error.
        """

        tasks = []

        available_packages = self.manager.list_available_packages()
        if not available_packages:
            return False

        if found_packages is None:
            found_packages = self.manager.list_packages()
        renamed_packages = self.manager.settings.get('renamed_packages', {})

        # VCS package updates
        ignore_vcs_packages = self.PULL not in actions
        if not ignore_vcs_packages:
            ignore_vcs_packages = self.manager.settings.get('ignore_vcs_packages', False)

        executor = futures.ThreadPoolExecutor(max_workers=10)
        vcs_futures = []

        def create_vcs_task(upgrader, package_name):
            if not upgrader.incoming():
                return None
            return PackageInstallTask(self.PULL, package_name, upgrader=upgrader)

        # packages to upgrade
        for package_name in found_packages:
            if include_packages and package_name not in include_packages:
                continue
            if ignore_packages and package_name in ignore_packages:
                continue

            # VCS package updates
            upgrader = self.manager.instantiate_upgrader(package_name)
            if upgrader:
                if self.PULL not in actions:
                    continue
                if ignore_vcs_packages is True:
                    continue
                if isinstance(ignore_vcs_packages, list) and package_name in ignore_vcs_packages:
                    continue

                vcs_futures.append(executor.submit(create_vcs_task, upgrader, package_name))
                continue

            # if a package was renamed, new name is to be used to lookup update info
            new_package_name = renamed_packages.get(package_name) or package_name
            update_info = available_packages.get(new_package_name)
            if not update_info:
                continue

            package_version = None

            metadata = self.manager.get_metadata(package_name)
            if metadata:
                package_version = metadata.get('version')
                if package_version:
                    package_version = PackageVersion(package_version)

            if package_version:
                version = PackageVersion(update_info['releases'][0]['version'])
                if version > package_version:
                    action = self.UPGRADE
                elif version < package_version:
                    action = self.DOWNGRADE
                else:
                    action = self.REINSTALL
            else:
                action = self.OVERWRITE

            if action in actions:
                tasks.append(PackageInstallTask(action, package_name, package_version, update_info))

        # add results from vcs upgraders
        vcs_futures = futures.wait(vcs_futures)
        for future in vcs_futures.done:
            task = future.result()
            if task:
                tasks.append(task)

        # packages to install
        if self.INSTALL in actions:
            for package_name, update_info in available_packages.items():
                if package_name in found_packages:
                    continue
                if include_packages and package_name not in include_packages:
                    continue
                if ignore_packages and package_name in ignore_packages:
                    continue
                tasks.append(PackageInstallTask(self.INSTALL, package_name, update_info=update_info))

        return sorted(tasks, key=lambda task: task.package_name.lower())

    def render_quick_panel_items(self, tasks):
        """
        Create a list of quick panel items for specified tasks.

        :param tasks:
            A ``PackageInstallTask`` object.

        :returns:
            A list of ``QuickPanelItem`` objects if supported or a list of
            lists of three unicode strings (name, description, extra) otherwise.
        """

        items = []

        for task in tasks:
            action = task.action
            if action == self.INSTALL or action == self.REINSTALL:
                extra = ' v{}'.format(task.available_version)
            elif action == self.DOWNGRADE or action == self.UPGRADE:
                extra = ' to v{} from v{}'.format(task.available_version, task.package_version)
            elif action == self.OVERWRITE:
                extra = ' v{} with v{}'.format(task.package_version, task.available_version)
            elif action == self.PULL:
                extra = ' with {}'.format(task.upgrader.cli_name)
            else:
                action = ''
                extra = ''

            final_line = action + extra

            if USE_QUICK_PANEL_ITEM:
                description = '<em>{}</em>'.format(html.escape(task.package_description))

                if final_line:
                    final_line = '<em>{}</em>'.format(final_line)

                homepage = html.escape(task.package_homepage)
                homepage_display = re.sub(r'^https?://', '', homepage)
                if homepage_display:
                    if final_line:
                        final_line += ' '
                    final_line += '<a href="{}">{}</a>'.format(homepage, homepage_display)

                annotation = ''
                if task.last_modified:
                    try:
                        # strip time as it is not of interrest and to be permissive with repos,
                        # which don't provide full timestamp.
                        date, _ = task.last_modified.split(' ', 1)
                        annotation = datetime.strptime(date, '%Y-%m-%d').strftime('Updated on %a %b %d, %Y')
                    except ValueError:
                        pass

                items.append(sublime.QuickPanelItem(task.package_name, [description, final_line], annotation))

            else:
                homepage_display = re.sub(r'^https?://', '', task.package_homepage)
                if final_line and homepage_display:
                    final_line += ' '
                final_line += homepage_display

                items.append([task.package_name, task.package_description, final_line])

        return items
