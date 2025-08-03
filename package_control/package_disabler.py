import json
import os
from threading import RLock

import sublime

try:
    # Relative import does not work here due to hard loading events
    # into global package_control (see bootstrap.py)!
    from package_control import events
except Exception:
    # use relative import, if bootstrapping has not yet been completed
    from . import events

from .console_write import console_write
from .package_io import package_file_exists, read_package_file
from .settings import (
    preferences_filename,
    pc_settings_filename,
    load_list_setting,
    save_list_setting
)
from .show_error import show_error
from .sys_path import pc_cache_dir


class PackageDisabler:

    DISABLE = 'disable'
    """
    A key used to create package_actions for disable_packages or reenable_packages.
    """

    ENABLE = 'enable'
    """
    A key used to create package_actions for disable_packages or reenable_packages.
    """

    INSTALL = 'install'
    """
    A key used to create package_actions for disable_packages or reenable_packages.
    """

    REMOVE = 'remove'
    """
    A key used to create package_actions for disable_packages or reenable_packages.
    """

    UPGRADE = 'upgrade'
    """
    A key used to create package_actions for disable_packages or reenable_packages.
    """

    LOADER = 'loader'
    """
    A key used to create package_actions for disable_packages or reenable_packages.
    """

    color_scheme_packages = {}
    """
    A dictionary of packages, containing a color scheme.

    Keys are color scheme names without file extension.
    The values are sets of package names, owning the color scheme.

    {
        'Mariana': {'Color Scheme - Default', 'User'},
    }
    """

    theme_packages = {}
    """
    A dictionary of packages, containing a theme.

    Keys are theme names without file extension.
    The values are sets of package names, owning the theme.

    {
        'Default': {'Theme - Default', 'User'},
    }
    """

    default_themes = {}
    """
    A dictionary of default theme settings.

    Sublime Text 3:

    {
        "theme": "Default.sublime-color-scheme"
    }

    Sublime Text 4

    {
        "theme": "auto"
        "dark_theme": "Default Dark.sublime-color-scheme"
        "light_theme": "Default.sublime-color-scheme"
    }
    """

    global_themes = {}
    """
    A dictionary of stored theme settings.
    """

    default_color_schemes = {}
    """
    A dictionary of default color scheme settings.

    Sublime Text 3:

    {
        "color_scheme": "Mariana.sublime-color-scheme"
    }

    Sublime Text 4

    {
        "color_scheme": "Mariana.sublime-color-scheme"
        "dark_color_scheme": "Mariana.sublime-color-scheme"
        "light_color_scheme": "Breakets.sublime-color-scheme"
    }
    """

    global_color_schemes = {}
    """
    A dictionary of stored color scheme settings.
    """

    view_color_schemes = {}
    """
    A dictionary of view-specific color scheme settings.

    Sublime Text 3:

    {
        <view_id>: {
            "color_scheme": "Mariana.sublime-color-scheme"
        },
        ...
    }

    Sublime Text 4

    {
        <view_id>: {
            "color_scheme": "Mariana.sublime-color-scheme"
            "dark_color_scheme": "Mariana.sublime-color-scheme"
            "light_color_scheme": "Breakets.sublime-color-scheme"
        },
        ...
    }
    """

    view_syntaxes = {}
    """
    A dictionary of view-specifix syntax settings.

    {
        <view_id>: "Packages/Text/Plain Text.tmLanguage"
    }
    """

    lock = RLock()
    refcount = 0

    @staticmethod
    def ignored_packages():
        with PackageDisabler.lock:
            settings = sublime.load_settings(preferences_filename())
            return load_list_setting(settings, 'ignored_packages')

    @staticmethod
    def in_progress_packages():
        with PackageDisabler.lock:
            settings = sublime.load_settings(pc_settings_filename())
            return load_list_setting(settings, 'in_progress_packages')

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
    def disable_packages(package_actions):
        """
        Disables one or more packages before installing or upgrading to prevent
        errors where Sublime Text tries to read files that no longer exist, or
        read a half-written file.

        :param package_actions:
            A dictionary of actions for a set of packages.

            ``{action: {packages}}``

            The key is an `action` that caused the packages to be disabled:

             - PackageDisabler.DISABLE
             - PackageDisabler.ENABLE
             - PackageDisabler.INSTALL
             - PackageDisabler.REMOVE
             - PackageDisabler.UPGRADE
             - PackageDisabler.LOADER (deprecated)

            The value can be a package name string, or an array of strings

        :return:
            A set of package names that were disabled
        """

        with PackageDisabler.lock:
            settings = sublime.load_settings(preferences_filename())
            ignored_at_start = load_list_setting(settings, 'ignored_packages')
            ignored = set()

            pc_settings = sublime.load_settings(pc_settings_filename())
            in_process_at_start = load_list_setting(pc_settings, 'in_process_packages')
            in_process = set()

            need_restore = False
            affected = set()

            for action, packages in package_actions.items():
                # convert packages to a set
                if not isinstance(packages, set):
                    if isinstance(packages, (list, tuple)):
                        packages = set(packages)
                    else:
                        packages = {packages}

                disabled = packages - (ignored_at_start - in_process_at_start)
                affected |= disabled
                ignored |= ignored_at_start | disabled

                # Clear packages from in-progress when disabling them, otherwise
                # they automatically get re-enabled the next time Sublime Text starts
                if action == PackageDisabler.DISABLE:
                    in_process |= in_process_at_start - packages

                # Make sure to re-enable installed or removed packages,
                # even if they were disabled before.
                elif action == PackageDisabler.INSTALL or action == PackageDisabler.REMOVE:
                    in_process |= in_process_at_start | packages

                # Keep disabled packages disabled after update
                else:
                    in_process |= in_process_at_start | disabled

                # Derermine whether to Backup old color schemes, syntaxes and theme for later restore.
                # If False, reset to defaults only.
                need_restore |= action in (PackageDisabler.INSTALL, PackageDisabler.UPGRADE)

                if action == PackageDisabler.UPGRADE:
                    for package in disabled:
                        version = PackageDisabler.get_version(package)
                        events.add(events.PRE_UPGRADE, package, version)

                elif action == PackageDisabler.REMOVE:
                    for package in disabled:
                        version = PackageDisabler.get_version(package)
                        events.add(events.REMOVE, package, version)

            PackageDisabler.backup_and_reset_settings(affected, need_restore)

            save_list_setting(
                pc_settings,
                pc_settings_filename(),
                'in_process_packages',
                in_process,
                in_process_at_start
            )

            save_list_setting(
                settings,
                preferences_filename(),
                'ignored_packages',
                ignored,
                ignored_at_start
            )

            return affected

    @staticmethod
    def reenable_packages(package_actions):
        """
        Re-enables packages after they have been installed or upgraded

        :param package_actions:
            A dictionary of actions for a set of packages.

            ``{action: {packages}}``

            The key is an `action` that caused the packages to be disabled:

             - PackageDisabler.DISABLE
             - PackageDisabler.ENABLE
             - PackageDisabler.INSTALL
             - PackageDisabler.REMOVE
             - PackageDisabler.UPGRADE
             - PackageDisabler.LOADER (deprecated)

            The value can be a package name string, or an array of strings
        """

        with PackageDisabler.lock:
            settings = sublime.load_settings(preferences_filename())
            ignored = load_list_setting(settings, 'ignored_packages')

            pc_settings = sublime.load_settings(pc_settings_filename())
            in_process = load_list_setting(pc_settings, 'in_process_packages')

            need_restore = False
            affected = set()

            try:
                for action, packages in package_actions.items():
                    # convert packages to a set
                    if not isinstance(packages, set):
                        if isinstance(packages, (list, tuple)):
                            packages = set(packages)
                        else:
                            packages = {packages}

                    if action == PackageDisabler.INSTALL:
                        packages &= in_process
                        for package in packages:
                            version = PackageDisabler.get_version(package)
                            events.add(events.INSTALL, package, version)
                            events.clear(events.INSTALL, package, future=True)
                        need_restore = True

                    elif action == PackageDisabler.UPGRADE:
                        packages &= in_process
                        for package in packages:
                            version = PackageDisabler.get_version(package)
                            events.add(events.POST_UPGRADE, package, version)
                            events.clear(events.POST_UPGRADE, package, future=True)
                            events.clear(events.PRE_UPGRADE, package)
                        need_restore = True

                    elif action == PackageDisabler.REMOVE:
                        packages &= in_process
                        for package in packages:
                            events.clear(events.REMOVE, package)

                    affected |= packages

                # always flush settings to disk
                # to make sure to also save updated `installed_packages`
                save_list_setting(
                    pc_settings,
                    pc_settings_filename(),
                    'in_process_packages',
                    in_process - affected
                )

                save_list_setting(
                    settings,
                    preferences_filename(),
                    'ignored_packages',
                    ignored - affected,
                    ignored
                )

            finally:
                # restore settings after installing missing packages or upgrades
                if need_restore:
                    # By delaying the restore, we give Sublime Text some time to
                    # re-enable packages, making errors less likely
                    sublime.set_timeout_async(PackageDisabler.restore_settings, 4000)

    @staticmethod
    def init_default_settings():
        """
        Initializes the default settings from ST's Default/Preferences.sublime-settings.

        Make sure to have correct default values available based on ST version.
        """

        if PackageDisabler.default_themes:
            return

        resource_name = 'Packages/Default/Preferences.sublime-settings'
        settings = sublime.decode_value(sublime.load_resource(resource_name))

        for key in ('color_scheme', 'dark_color_scheme', 'light_color_scheme'):
            value = settings.get(key)
            if value:
                PackageDisabler.default_color_schemes[key] = value

        for key in ('theme', 'dark_theme', 'light_theme'):
            value = settings.get(key)
            if value:
                PackageDisabler.default_themes[key] = value

    @staticmethod
    def backup_and_reset_settings(packages, backup):
        """
        Backup and reset color scheme, syntax or theme contained by specified packages

        :param packages:
            A set of package names which trigger backup and reset of settings.

        :param backup:
            If ``True`` old values are backed up for later restore.
            If ``False`` reset values to defaults only.
        """

        PackageDisabler.init_default_settings()

        settings = sublime.load_settings(preferences_filename())
        cached_settings = {}

        if backup:
            if PackageDisabler.refcount == 0:
                PackageDisabler.disable_indexer()

            PackageDisabler.refcount += 1

        # Backup and reset global theme(s)
        for key, default_file in PackageDisabler.default_themes.items():
            theme_file = settings.get(key)
            if theme_file in (None, '', 'auto', default_file):
                continue
            theme_name, theme_packages = find_theme_packages(theme_file)
            theme_packages &= packages
            if not theme_packages:
                continue
            if backup:
                if theme_name not in PackageDisabler.theme_packages:
                    PackageDisabler.theme_packages[theme_name] = theme_packages
                else:
                    PackageDisabler.theme_packages[theme_name] |= theme_packages
                PackageDisabler.global_themes[key] = theme_file
            settings.set(key, default_file)

        # Backup and reset global color scheme(s)
        #
        # Modern *.sublime-color-schme files may exist in several packages.
        # If one of them gets inaccessible, the merged color scheme breaks.
        # So any related package needs to be monitored. Special treatment is needed
        # for *.tmTheme files, too as they can be overridden by *.sublime-color-schemes.
        for key, default_file in PackageDisabler.default_color_schemes.items():
            scheme_file = settings.get(key)
            cached_settings[key] = scheme_file
            if scheme_file in (None, '', 'auto', default_file):
                continue
            scheme_name, scheme_packages = find_color_scheme_packages(scheme_file)
            scheme_packages &= packages
            if not scheme_packages:
                continue
            if backup:
                if scheme_name not in PackageDisabler.color_scheme_packages:
                    PackageDisabler.color_scheme_packages[scheme_name] = scheme_packages
                else:
                    PackageDisabler.color_scheme_packages[scheme_name] |= scheme_packages
                PackageDisabler.global_color_schemes[key] = scheme_file
            settings.set(key, default_file)

        for window in sublime.windows():
            # create a list of real and output panel views
            views = window.views()
            for panel_name in filter(lambda p: p.startswith('output.'), window.panels()):
                panel = window.find_output_panel(panel_name[len('output.'):])
                views.append(panel)

            for view in views:
                view_settings = view.settings()

                # Backup and reset view-specific color schemes not already taken care
                # of by resetting the global color scheme above
                for key, default_file in PackageDisabler.default_color_schemes.items():
                    scheme_file = view_settings.get(key)
                    if scheme_file in (None, '', 'auto', default_file, cached_settings[key]):
                        continue
                    scheme_name, scheme_packages = find_color_scheme_packages(scheme_file)
                    scheme_packages &= packages
                    if not scheme_packages:
                        continue
                    if backup:
                        if scheme_name not in PackageDisabler.color_scheme_packages:
                            PackageDisabler.color_scheme_packages[scheme_name] = scheme_packages
                        else:
                            PackageDisabler.color_scheme_packages[scheme_name] |= scheme_packages
                        PackageDisabler.view_color_schemes.setdefault(view.id(), {})[key] = scheme_file
                    # drop view specific color scheme to fallback to global one
                    # and keep it active in case this one can't be restored
                    view_settings.erase(key)

                # Backup and reset assigned syntaxes
                syntax = view_settings.get('syntax')
                if syntax and isinstance(syntax, str) and any(
                    syntax.startswith('Packages/' + package + '/') for package in packages
                ):
                    if backup:
                        PackageDisabler.view_syntaxes[view.id()] = syntax
                    view_settings.set('syntax', 'Packages/Text/Plain text.tmLanguage')

    @staticmethod
    def restore_settings():
        with PackageDisabler.lock:
            PackageDisabler.refcount -= 1
            if PackageDisabler.refcount > 0:
                return

            color_scheme_errors = set()
            syntax_errors = set()

            settings = sublime.load_settings(preferences_filename())
            save_settings = False

            try:
                # restore global theme
                all_missing_theme_packages = set()

                for key, theme_file in PackageDisabler.global_themes.items():
                    theme_name, theme_packages = find_theme_packages(theme_file)
                    missing_theme_packages = PackageDisabler.theme_packages[theme_name] - theme_packages
                    if missing_theme_packages:
                        all_missing_theme_packages |= missing_theme_packages
                    else:
                        settings.set(key, theme_file)
                        save_settings = True

                if all_missing_theme_packages:
                    show_error(
                        '''
                        The following packages no longer participate in your active theme after upgrade.

                           - %s

                        As one of them may contain the primary theme, Sublime Text is configured
                        to use the default theme to prevent you ending up with a broken UI.
                        ''',
                        '\n   - '.join(sorted(all_missing_theme_packages, key=lambda s: s.lower()))
                    )

                # restore global color scheme
                all_missing_scheme_packages = set()

                for key, scheme_file in PackageDisabler.global_color_schemes.items():
                    scheme_name, scheme_packages = find_color_scheme_packages(scheme_file)
                    missing_scheme_packages = PackageDisabler.color_scheme_packages[scheme_name] - scheme_packages
                    if missing_scheme_packages:
                        all_missing_scheme_packages |= missing_scheme_packages
                    else:
                        settings.set(key, scheme_file)
                        save_settings = True

                if all_missing_scheme_packages:
                    show_error(
                        '''
                        The following packages no longer participate in your active color scheme after upgrade.

                           - %s

                        As one of them may contain the primary color scheme, Sublime Text is configured
                        to use the default color scheme to prevent you ending up with a broken UI.
                        ''',
                        '\n   - '.join(sorted(all_missing_scheme_packages, key=lambda s: s.lower()))
                    )

                # restore viewa-specific color scheme assignments
                for view_id, view_schemes in PackageDisabler.view_color_schemes.items():
                    view = sublime.View(view_id)
                    if not view.is_valid():
                        continue
                    for key, scheme_file in view_schemes.items():
                        if scheme_file in color_scheme_errors:
                            continue
                        scheme_name, scheme_packages = find_color_scheme_packages(scheme_file)
                        missing_scheme_packages = PackageDisabler.color_scheme_packages[scheme_name] - scheme_packages
                        if missing_scheme_packages:
                            console_write('The color scheme "%s" no longer exists' % scheme_file)
                            color_scheme_errors.add(scheme_file)
                            continue
                        view.settings().set(key, scheme_file)

                # restore syntax assignments
                for view_id, syntax in PackageDisabler.view_syntaxes.items():
                    view = sublime.View(view_id)
                    if not view.is_valid() or syntax in syntax_errors:
                        continue
                    if not resource_exists(syntax):
                        console_write('The syntax "%s" no longer exists' % syntax)
                        syntax_errors.add(syntax)
                        continue
                    view.settings().set('syntax', syntax)

            finally:
                save_settings |= PackageDisabler.resume_indexer(False)
                if save_settings:
                    sublime.save_settings(preferences_filename())

                PackageDisabler.color_scheme_packages = {}
                PackageDisabler.theme_packages = {}

                PackageDisabler.global_color_schemes = {}
                PackageDisabler.global_themes = {}

                PackageDisabler.view_color_schemes = {}
                PackageDisabler.view_syntaxes = {}

                PackageDisabler.refcount = 0

    @staticmethod
    def disable_indexer():
        # Temporarily disable indexing during package updates, so multiple syntax
        # packages can be disabled/installed and re-enabled without indexer restarting
        # for each one individually. Also we don't want to re-index while a syntax
        # package is being disabled for upgrade - just once after upgrade is finished.
        settings = sublime.load_settings(preferences_filename())
        index_files = settings.get('index_files', True)
        if index_files:
            try:
                # note: uses persistent cookie to survive PC updates.
                with open(os.path.join(pc_cache_dir(), 'backup.json'), 'x', encoding='utf-8') as fobj:
                    json.dump({'index_files': index_files}, fobj)
                settings.set('index_files', False)
                console_write('pausing indexer')
            except OSError:
                pass

    @staticmethod
    def resume_indexer(persist=True):
        result = False
        backup_json = os.path.join(pc_cache_dir(), 'backup.json')
        try:
            with open(backup_json, 'r', encoding='utf-8') as fobj:
                if json.load(fobj).get('index_files') is True:
                    settings_file = preferences_filename()
                    settings = sublime.load_settings(settings_file)
                    settings.set('index_files', True)
                    if persist:
                        sublime.save_settings(settings_file)
                    console_write('resuming indexer')
                    result = True
        except FileNotFoundError:
            pass
        except Exception as e:
            console_write('failed to resume indexer! %s', e)

        try:
            os.remove(backup_json)
        except OSError:
            pass

        return result


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
        The color scheme settings value

    :returns:
        A tuple of color scheme name and a set of package names containing it

        ( 'Mariana', { 'Color Scheme - Default', 'User' } )
    """

    packages = set()
    name = os.path.basename(os.path.splitext(color_scheme)[0])

    for ext in ('.sublime-color-scheme', '.tmTheme'):
        for path in sublime.find_resources(name + ext):
            parts = path[9:].split('/', 1)
            if len(parts) == 2:
                packages.add(parts[0])

    return name, packages


def find_theme_packages(theme):
    """
    Build a set of packages, containing the theme.

    :param theme:
        The theme settings value

    :returns:
        A tuple of theme name and a set of package names containing it

        ( 'Default', { 'Theme - Default', 'User' } )
    """

    packages = set()
    file_name = os.path.basename(theme)
    name = os.path.splitext(file_name)[0]

    for path in sublime.find_resources(file_name):
        parts = path[9:].split('/', 1)
        if len(parts) == 2:
            packages.add(parts[0])

    return name, packages
