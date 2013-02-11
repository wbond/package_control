import json

from ..console_write import console_write
from .platform_comparator import PlatformComparator


class ChannelProvider(PlatformComparator):
    """
    Retrieves a channel and provides an API into the information

    The current channel/repository infrastructure caches repository info into
    the channel to improve the Package Control client performance. This also
    has the side effect of lessening the load on the GitHub and BitBucket APIs
    and getting around not-infrequent HTTP 503 errors from those APIs.

    :param channel:
        The URL of the channel

    :param package_manager:
        An instance of :class:`PackageManager` used to download the file
    """

    def __init__(self, channel, package_manager):
        self.channel_info = None
        self.channel = channel
        self.package_manager = package_manager
        self.unavailable_packages = []

    def match_url(self):
        """Indicates if this provider can handle the provided channel"""

        return True

    def fetch_channel(self):
        """Retrieves and loads the JSON for other methods to use"""

        if self.channel_info != None:
            return

        channel_json = self.package_manager.download_url(self.channel,
            'Error downloading channel.')
        if channel_json == False:
            self.channel_info = False
            return

        try:
            channel_info = json.loads(channel_json.decode('utf-8'))
        except (ValueError):
            console_write(u'Error parsing JSON from channel %s.' % self.channel, True)
            channel_info = False

        schema_error = u'Channel %s does not appear to be a valid channel file because ' % self.channel

        if 'schema_version' not in channel_info:
            console_write(u'%s the "schema_version" JSON key is missing.' % schema_error, True)
            self.channel_info = False
            return

        if str(channel_info['schema_version']) not in ['1.0', '1.1', '1.2']:
            console_write(u'%s the "schema_version" is not recognized. Must be one of: 1.0, 1.1 or 1.2.' % schema_error, True)
            self.channel_info = False
            return

        self.channel_info = channel_info

    def get_name_map(self):
        """:return: A dict of the mapping for URL slug -> package name"""

        self.fetch_channel()
        if self.channel_info == False:
            return False
        return self.channel_info.get('package_name_map', {})

    def get_renamed_packages(self):
        """:return: A dict of the packages that have been renamed"""

        self.fetch_channel()
        if self.channel_info == False:
            return False
        return self.channel_info.get('renamed_packages', {})

    def get_repositories(self):
        """:return: A list of the repository URLs"""

        self.fetch_channel()
        if self.channel_info == False:
            return False

        if 'repositories' not in self.channel_info:
            console_write(u'Channel %s does not appear to be a valid channel file because the "repositories" JSON key is missing.' % self.channel, True)
            return False

        return self.channel_info.get('repositories', {})

    def get_certs(self):
        """
        Provides a secure way for distribution of SSL CA certificates

        Unfortunately Python does not include a bundle of CA certs with urllib
        to perform SSL certificate validation. To circumvent this issue,
        Package Control acts as a distributor of the CA certs for all HTTPS
        URLs of package downloads.

        The default channel scrapes and caches info about all packages
        periodically, and in the process it checks the CA certs for all of
        the HTTPS URLs listed in the repositories. The contents of the CA cert
        files are then hashed, and the CA cert is stored in a filename with
        that hash. This is a fingerprint to ensure that Package Control has
        the appropriate CA cert for a domain name.

        Next, the default channel file serves up a JSON object of the domain
        names and the hashes of their current CA cert files. If Package Control
        does not have the appropriate hash for a domain, it may retrieve it
        from the channel server. To ensure that Package Control is talking to
        a trusted authority to get the CA certs from, the CA cert for
        sublime.wbond.net is bundled with Package Control. Then when downloading
        the channel file, Package Control can ensure that the channel file's
        SSL certificate is valid, thus ensuring the resulting CA certs are
        legitimate.

        As a matter of optimization, the distribution of Package Control also
        includes the current CA certs for all known HTTPS domains that are
        included in the channel, as of the time when Package Control was
        last released.

        :return: A dict of {'Domain Name': ['cert_file_hash', 'cert_file_download_url']}
        """

        self.fetch_channel()
        if self.channel_info == False:
            return False
        return self.channel_info.get('certs', {})

    def get_packages(self, repo):
        """
        Provides access to the repository info that is cached in a channel

        :param repo:
            The URL of the repository to get the cached info of

        :return:
            A dict in the format:
            {
                'Package Name': {
                    # Package details - see example-packages.json for format
                },
                ...
            }
            or False if there is an error
        """

        self.fetch_channel()
        if self.channel_info == False:
            return False
        if self.channel_info.get('packages', False) == False:
            return False
        if self.channel_info['packages'].get(repo, False) == False:
            return False

        output = {}
        for package in self.channel_info['packages'][repo]:
            copy = package.copy()

            platforms = list(copy['platforms'].keys())
            best_platform = self.get_best_platform(platforms)

            if not best_platform:
                self.unavailable_packages.append(copy['name'])
                continue

            copy['downloads'] = copy['platforms'][best_platform]

            del copy['platforms']

            copy['url'] = copy['homepage']
            del copy['homepage']

            output[copy['name']] = copy

        return output

    def get_unavailable_packages(self):
        """
        Provides a list of packages that are unavailable for the current
        platform/architecture that Sublime Text is running on.

        This list will be empty unless get_packages() is called first.

        :return: A list of package names
        """

        return self.unavailable_packages
