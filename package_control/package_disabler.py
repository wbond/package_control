import functools
import json
import os
import threading

import sublime

from . import events
from .console_write import console_write
from .package_io import package_file_exists, read_package_file
from .settings import (
    preferences_filename,
    pc_settings_filename,
    load_list_setting,
    load_list_setting_as_set,
    save_list_setting
)
from .show_error import show_error


class PackageDisabler:
    old_color_scheme_packages = set()
    old_color_scheme = None

    old_theme_packages = set()
    old_theme = None

    old_syntaxes = []
    old_color_schemes = []

    lock = threading.Lock()
    restore_id = 0

    @staticmethod
    def get_ignored_packages():
        with PackageDisabler.lock:
            settings = sublime.load_settings(preferences_filename())
            return load_list_setting(settings, 'ignored_packages')

    @staticmethod
    def set_ignored_packages(ignored):
        with PackageDisabler.lock:
            settings = sublime.load_settings(preferences_filename())
            save_list_setting(settings, preferences_filename(), 'ignored_packages', ignored)

    @staticmethod
    def get_version(package):
        """
        Gets the current version of a package

        :param package:
            The name of the package

        :return:
            The string version
        """

        metadata_json = read_package_file(package, 'package-metadata.json')
        if metadata_json:
            try:
                return json.loads(metadata_json).get('version', 'unknown version')
            except (ValueError):
                console_write(
                    '''
                    An error occurred while trying to parse package metadata for %s.
                    ''',
                    package
                )

        return 'unknown version'

    @staticmethod
    def disable_packages(packages, operation='upgrade'):
        """
        Disables one or more packages before installing or upgrading to prevent
        errors where Sublime Text tries to read files that no longer exist, or
        read a half-written file.

        :param packages:
            The string package name, or an array of strings

        :param operation:
            The type of operation that caused the package to be disabled:
             - "upgrade"
             - "remove"
             - "install"
             - "disable"
             - "loader" - deprecated

        :return:
            A set of package names that were disabled
        """

        with PackageDisabler.lock:
            settings = sublime.load_settings(preferences_filename())
            ignored = load_list_setting_as_set(settings, 'ignored_packages')

            pc_settings = sublime.load_settings(pc_settings_filename())
            in_process = load_list_setting_as_set(pc_settings, 'in_process_packages')

            if not isinstance(packages, (list, set, tuple)):
                packages = [packages]
            packages = set(packages)

            disabled = packages - ignored
            ignored |= disabled
            in_process |= disabled

            # Modern *.sublime-color-schme files may exist in several packages.
            # If one of them gets inaccessible, the merged color scheme breaks.
            # So any related package needs to be monitored. Special treatment is needed
            # for *.tmTheme files, too as they can be overridden by *.sublime-color-schemes.
            global_color_scheme = settings.get('color_scheme', '')
            global_color_scheme_packages = find_color_scheme_packages(global_color_scheme)
            if global_color_scheme_packages & disabled:
                PackageDisabler.old_color_scheme_packages |= global_color_scheme_packages
                PackageDisabler.old_color_scheme = global_color_scheme
                # Set default color scheme via tmTheme for compat with ST3143
                settings.set('color_scheme', 'Packages/Color Scheme - Default/Mariana.tmTheme')

            global_theme = settings.get('theme', '')
            global_theme_packages = find_theme_packages(global_theme)
            if global_theme_packages & disabled:
                PackageDisabler.old_theme_packages |= global_theme_packages
                PackageDisabler.old_theme = global_theme
                # Set default color scheme via tmTheme for compat with ST3143
                settings.set('theme', 'Default.sublime-theme')

            for window in sublime.windows():
                for view in window.views():
                    view_settings = view.settings()

                    # Backup and reset view-specific color_scheme settings not already taken care
                    # of by resetting the global color_scheme above
                    color_scheme = view_settings.get('color_scheme')
                    if color_scheme is not None and color_scheme != global_color_scheme:
                        color_scheme_packages = find_color_scheme_packages(color_scheme)
                        if color_scheme_packages & disabled:
                            PackageDisabler.old_color_schemes.append([view, color_scheme, color_scheme_packages])
                            # Set default color scheme via tmTheme for compat with ST3143
                            view_settings.set('color_scheme', 'Packages/Color Scheme - Default/Mariana.tmTheme')

                    # Backup and reset assigned syntaxes
                    syntax = view_settings.get('syntax')
                    if syntax is not None and any(
                        syntax.startswith('Packages/' + package + '/') for package in disabled
                    ):
                        PackageDisabler.old_syntaxes.append([view, syntax])
                        view_settings.set('syntax', 'Packages/Text/Plain text.tmLanguage')

            if operation == 'upgrade':
                for package in disabled:
                    version = PackageDisabler.get_version(package)
                    events.add('pre_upgrade', package, version)

            elif operation == 'remove':
                for package in disabled:
                    version = PackageDisabler.get_version(package)
                    events.add(operation, package, version)

            # We don't mark a package as in-process when disabling it, otherwise
            # it automatically gets re-enabled the next time Sublime Text starts
            if operation != 'disable':
                save_list_setting(pc_settings, pc_settings_filename(), 'in_process_packages', in_process)

            save_list_setting(settings, preferences_filename(), 'ignored_packages', ignored)

            return disabled

    @staticmethod
    def reenable_packages(packages, operation='upgrade'):
        """
        Re-enables packages after they have been installed or upgraded

        :param packages:
            The string package name, or an array of strings

        :param operation:
            The type of operation that caused the package to be re-enabled:
             - "upgrade"
             - "remove"
             - "install"
             - "enable"
             - "loader" - deprecated
        """

        with PackageDisabler.lock:
            settings = sublime.load_settings(preferences_filename())
            ignored = load_list_setting_as_set(settings, 'ignored_packages')

            pc_settings = sublime.load_settings(pc_settings_filename())
            in_process = load_list_setting_as_set(pc_settings, 'in_process_packages')

            if not isinstance(packages, (list, set, tuple)):
                packages = [packages]
            packages = set(packages) & ignored

            if operation == 'install':
                for package in packages:
                    version = PackageDisabler.get_version(package)
                    events.add(operation, package, version)
                    events.clear(operation, package, future=True)

            elif operation == 'upgrade':
                for package in packages:
                    version = PackageDisabler.get_version(package)
                    events.add('post_upgrade', package, version)
                    events.clear('post_upgrade', package, future=True)
                    events.clear('pre_upgrade', package)

            elif operation == 'remove':
                for package in packages:
                    events.clear('remove', package)

            ignored -= packages
            save_list_setting(settings, preferences_filename(), 'ignored_packages', ignored)

            in_process -= packages
            save_list_setting(pc_settings, pc_settings_filename(), 'in_process_packages', in_process)

            if operation == 'upgrade':
                # By delaying the restore, we give Sublime Text some time to
                # re-enable packages, making errors less likely
                PackageDisabler.restore_id += 1
                sublime.set_timeout(functools.partial(
                    PackageDisabler.delayed_settings_restore, PackageDisabler.restore_id), 1000)

    @staticmethod
    def delayed_settings_restore(restore_id):

        if restore_id != PackageDisabler.restore_id:
            return

        with PackageDisabler.lock:
            color_scheme_errors = set()
            syntax_errors = set()

            settings = sublime.load_settings(preferences_filename())
            save_settings = False

            try:
                # restore global theme
                if PackageDisabler.old_theme:
                    theme_packages = find_theme_packages(PackageDisabler.old_theme)
                    missing_theme_packages = PackageDisabler.old_theme_packages - theme_packages
                    if missing_theme_packages:
                        show_error(
                            '''
                            The following packages no longer participate in your active theme after upgrade.

                               - %s

                            As one of tem may contain the primary theme package,
                            Sublime Text is configured to use the default theme.
                            ''',
                            '\n   - '.join(sorted(missing_theme_packages, key=lambda s: s.lower()))
                        )
                    else:
                        save_settings = True
                        settings.set('theme', PackageDisabler.old_theme)

                # restore global color scheme
                if PackageDisabler.old_color_scheme:
                    color_scheme_packages = find_color_scheme_packages(PackageDisabler.old_color_scheme)
                    missing_color_scheme_packages = PackageDisabler.old_color_scheme_packages - color_scheme_packages
                    if missing_color_scheme_packages:
                        show_error(
                            '''
                            The following packages no longer participate in your active color scheme after upgrade.

                               - %s

                            As one of them may contain the primary color scheme,
                            Sublime Text is configured to use the default color scheme.
                            ''',
                            '\n   - '.join(sorted(missing_color_scheme_packages, key=lambda s: s.lower()))
                        )
                    else:
                        save_settings = True
                        settings.set('color_scheme', PackageDisabler.old_color_scheme)

                # restore viewa-specific color scheme assignments
                for view, color_scheme, old_color_scheme_packages in PackageDisabler.old_color_schemes:
                    if not view.is_valid() or color_scheme in color_scheme_errors:
                        continue
                    color_scheme_packages = find_color_scheme_packages(color_scheme)
                    missing_color_scheme_packages = old_color_scheme_packages - color_scheme_packages
                    if missing_color_scheme_packages:
                        console_write('The color scheme "%s" no longer exists' % color_scheme)
                        color_scheme_errors.add(color_scheme)
                        continue
                    view.settings().set('color_scheme', color_scheme)

                # restore syntax assignments
                for view, syntax in PackageDisabler.old_syntaxes:
                    if not view.is_valid() or syntax in syntax_errors:
                        continue
                    if not resource_exists(syntax):
                        console_write('The syntax "%s" no longer exists' % syntax)
                        syntax_errors.add(syntax)
                        continue
                    view.settings().set('syntax', syntax)

            finally:
                if save_settings:
                    sublime.save_settings(preferences_filename())

                PackageDisabler.old_color_scheme_packages.clear()
                PackageDisabler.old_color_scheme = None

                PackageDisabler.old_color_schemes.clear()
                PackageDisabler.old_syntaxes.clear()

                PackageDisabler.old_theme_packages.clear()
                PackageDisabler.old_theme = None

                PackageDisabler.restore_id = 0


def resource_exists(path):
    """
    Checks to see if a file exists

    :param path:
        A unicode string of a resource path, e.g. Packages/Package Name/resource_name.ext

    :return:
        A bool if it exists
    """

    if not path.startswith('Packages/'):
        return False

    parts = path[9:].split('/', 1)
    if len(parts) != 2:
        return False

    package_name, relative_path = parts
    return package_file_exists(package_name, relative_path)


def find_color_scheme_packages(color_scheme):
    """
    Build a set of packages, containing the color_scheme.

    :param color_scheme:
        The color scheme name

    :returns:
        A set of package names
    """

    packages = set()
    name = os.path.basename(os.path.splitext(color_scheme)[0])

    for ext in ('.sublime-color-scheme', '.tmTheme'):
        for path in sublime.find_resources(name + ext):
            parts = path[9:].split('/', 1)
            if len(parts) == 2:
                packages.add(parts[0])

    return packages


def find_theme_packages(theme):
    """
    Build a set of packages, containing the theme.

    :param theme:
        The color scheme name

    :returns:
        A set of package names
    """

    packages = set()

    for path in sublime.find_resources(os.path.basename(theme)):
        parts = path[9:].split('/', 1)
        if len(parts) == 2:
            packages.add(parts[0])

    return packages
