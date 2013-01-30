import sublime
import sys

# Make sure all dependencies are reloaded on upgrade
if 'package_control.reloader' in sys.modules:
    reload(sys.modules['package_control.reloader'])
import package_control.reloader

# Ensure the custom path entries have been loaded
import package_control.sys_path

# Commands
from package_control.commands.add_repository_channel_command import AddRepositoryChannelCommand
from package_control.commands.add_repository_command import AddRepositoryCommand
from package_control.commands.create_binary_package_command import CreateBinaryPackageCommand
from package_control.commands.create_package_command import CreatePackageCommand
from package_control.commands.disable_package_command import DisablePackageCommand
from package_control.commands.discover_packages_command import DiscoverPackagesCommand
from package_control.commands.enable_package_command import EnablePackageCommand
from package_control.commands.install_package_command import InstallPackageCommand
from package_control.commands.list_packages_command import ListPackagesCommand
from package_control.commands.remove_package_command import RemovePackageCommand
from package_control.commands.upgrade_all_packages_command import UpgradeAllPackagesCommand
from package_control.commands.upgrade_package_command import UpgradePackageCommand

from package_control.package_cleanup import PackageCleanup


# Start shortly after Sublime starts so package renames don't cause errors
# with keybindings, settings, etc disappearing in the middle of parsing
sublime.set_timeout(lambda: PackageCleanup().start(), 2000)
