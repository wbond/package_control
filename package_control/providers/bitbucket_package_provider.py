import re
import datetime

from .non_caching_provider import NonCachingProvider


class BitBucketPackageProvider(NonCachingProvider):
    """
    Allows using a public BitBucket repository as the source for a single package

    :param repo:
        The public web URL to the BitBucket repository. Should be in the format
        `https://bitbucket.org/user/package`.

    :param package_manager:
        An instance of :class:`PackageManager` used to access the API
    """

    def __init__(self, repo, package_manager):
        self.repo = repo
        self.package_manager = package_manager

    def match_url(self):
        """Indicates if this provider can handle the provided repo"""

        return re.search('^https?://bitbucket.org', self.repo) != None

    def get_packages(self):
        """Uses the BitBucket API to construct necessary info for a package"""

        api_url = re.sub('^https?://bitbucket.org/',
            'https://api.bitbucket.org/1.0/repositories/', self.repo)
        api_url = api_url.rstrip('/')

        repo_info = self.fetch_json(api_url)
        if repo_info == False:
            return False

        # Since HG allows for arbitrary main branch names, we have to hit
        # this URL just to get that info
        main_branch_url = api_url + '/main-branch/'
        main_branch_info = self.fetch_json(main_branch_url)
        if main_branch_info == False:
            return False

        # Grabbing the changesets is necessary because we construct the
        # version number from the last commit timestamp
        changeset_url = api_url + '/changesets/' + main_branch_info['name']
        last_commit = self.fetch_json(changeset_url)
        if last_commit == False:
            return False

        commit_date = last_commit['timestamp']
        timestamp = datetime.datetime.strptime(commit_date[0:19],
            '%Y-%m-%d %H:%M:%S')
        utc_timestamp = timestamp.strftime(
            '%Y.%m.%d.%H.%M.%S')

        homepage = repo_info['website']
        if not homepage:
            homepage = self.repo
        package = {
            'name': repo_info['name'],
            'description': repo_info['description'] if \
                repo_info['description'] else 'No description provided',
            'url': homepage,
            'author': repo_info['owner'],
            'last_modified': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'downloads': [
                {
                    'version': utc_timestamp,
                    'url': self.repo + '/get/' + \
                        last_commit['node'] + '.zip'
                }
            ]
        }
        return {package['name']: package}

    def get_renamed_packages(self):
        """For API-compatibility with :class:`PackageProvider`"""

        return {}
