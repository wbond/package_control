from .bitbucket_package_provider import BitBucketPackageProvider
from .github_package_provider import GitHubPackageProvider
from .github_user_provider import GitHubUserProvider
from .package_provider import PackageProvider

from .channel_provider import ChannelProvider


REPOSITORY_PROVIDERS = [BitBucketPackageProvider, GitHubPackageProvider,
    GitHubUserProvider, PackageProvider]

CHANNEL_PROVIDERS = [ChannelProvider]
