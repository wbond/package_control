import os

from .add_channel_command import AddChannelCommand
from .add_repository_command import AddRepositoryCommand
from .create_binary_package_command import CreateBinaryPackageCommand
from .create_package_command import CreatePackageCommand
from .disable_package_command import DisablePackageCommand
from .discover_packages_command import DiscoverPackagesCommand
from .enable_package_command import EnablePackageCommand
from .grab_certs_command import GrabCertsCommand
from .install_package_command import InstallPackageCommand
from .list_packages_command import ListPackagesCommand
from .remove_package_command import RemovePackageCommand
from .upgrade_all_packages_command import UpgradeAllPackagesCommand
from .upgrade_package_command import UpgradePackageCommand
from .package_message_command import PackageMessageCommand


__all__ = [
    'AddChannelCommand',
    'AddRepositoryCommand',
    'CreateBinaryPackageCommand',
    'CreatePackageCommand',
    'DisablePackageCommand',
    'DiscoverPackagesCommand',
    'EnablePackageCommand',
    'InstallPackageCommand',
    'ListPackagesCommand',
    'RemovePackageCommand',
    'UpgradeAllPackagesCommand',
    'UpgradePackageCommand',
    'PackageMessageCommand'
]

# Windows uses the wininet downloader, so it doesn't use the CA cert bundle
# and thus does not need the ability to grab to CA certs. Additionally,
# there is no openssl.exe on Windows.
if os.name != 'nt':
    __all__.append('GrabCertsCommand')
