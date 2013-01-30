import re
import datetime

from .non_caching_provider import NonCachingProvider


class GitHubUserProvider(NonCachingProvider):
    """
    Allows using a GitHub user/organization as the source for multiple packages

    :param repo:
        The public web URL to the GitHub user/org. Should be in the format
        `https://github.com/user`.

    :param package_manager:
        An instance of :class:`PackageManager` used to access the API
    """

    def __init__(self, repo, package_manager):
        self.repo = repo
        self.package_manager = package_manager

    def match_url(self):
        """Indicates if this provider can handle the provided repo"""

        return re.search('^https?://github.com/[^/]+/?$', self.repo) != None

    def get_packages(self):
        """Uses the GitHub API to construct necessary info for all packages"""

        user_match = re.search('^https?://github.com/([^/]+)/?$', self.repo)
        user = user_match.group(1)

        api_url = 'https://api.github.com/users/%s/repos?per_page=100' % user

        repo_info = self.fetch_json(api_url)
        if repo_info == False:
            return False

        packages = {}
        for package_info in repo_info:
            # All packages for the user are made available, and always from
            # the master branch. Anything else requires a custom packages.json
            commit_api_url = ('https://api.github.com/repos/%s/%s/commits' + \
                '?sha=master&per_page=1') % (user, package_info['name'])

            commit_info = self.fetch_json(commit_api_url)
            if commit_info == False:
                return False

            commit_date = commit_info[0]['commit']['committer']['date']
            timestamp = datetime.datetime.strptime(commit_date[0:19],
                '%Y-%m-%dT%H:%M:%S')
            utc_timestamp = timestamp.strftime(
                '%Y.%m.%d.%H.%M.%S')

            homepage = package_info['homepage']
            if not homepage:
                homepage = package_info['html_url']

            package = {
                'name': package_info['name'],
                'description': package_info['description'] if \
                    package_info['description'] else 'No description provided',
                'url': homepage,
                'author': package_info['owner']['login'],
                'last_modified': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'downloads': [
                    {
                        'version': utc_timestamp,
                        # We specifically use nodeload.github.com here because
                        # the download URLs all redirect there, and some of the
                        # downloaders don't follow HTTP redirect headers
                        'url': 'https://nodeload.github.com/' + \
                            package_info['owner']['login'] + '/' + \
                            package_info['name'] + '/zip/master'
                    }
                ]
            }
            packages[package['name']] = package
        return packages

    def get_renamed_packages(self):
        """For API-compatibility with :class:`PackageProvider`"""

        return {}
