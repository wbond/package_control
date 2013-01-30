try:
    # Python 3
    from urllib.parse import urlencode, quote
except (ImportError):
    # Python 2
    from urllib import urlencode, quote

import re
import datetime

from .non_caching_provider import NonCachingProvider


class GitHubPackageProvider(NonCachingProvider):
    """
    Allows using a public GitHub repository as the source for a single package

    :param repo:
        The public web URL to the GitHub repository. Should be in the format
        `https://github.com/user/package` for the master branch, or
        `https://github.com/user/package/tree/{branch_name}` for any other
        branch.

    :param package_manager:
        An instance of :class:`PackageManager` used to access the API
    """

    def __init__(self, repo, package_manager):
        # Clean off the trailing .git to be more forgiving
        self.repo = re.sub('\.git$', '', repo)
        self.package_manager = package_manager

    def match_url(self):
        """Indicates if this provider can handle the provided repo"""

        master = re.search('^https?://github.com/[^/]+/[^/]+/?$', self.repo)
        branch = re.search('^https?://github.com/[^/]+/[^/]+/tree/[^/]+/?$',
            self.repo)
        return master != None or branch != None

    def get_packages(self):
        """Uses the GitHub API to construct necessary info for a package"""

        branch = 'master'
        branch_match = re.search(
            '^https?://github.com/[^/]+/[^/]+/tree/([^/]+)/?$', self.repo)
        if branch_match != None:
            branch = branch_match.group(1)

        api_url = re.sub('^https?://github.com/([^/]+)/([^/]+)($|/.*$)',
            'https://api.github.com/repos/\\1/\\2', self.repo)

        repo_info = self.fetch_json(api_url)
        if repo_info == False:
            return False

        # In addition to hitting the main API endpoint for this repo, we
        # also have to list the commits to get the timestamp of the last
        # commit since we use that to generate a version number
        commit_api_url = api_url + '/commits?' + \
            urlencode({'sha': branch, 'per_page': 1})

        commit_info = self.fetch_json(commit_api_url)
        if commit_info == False:
            return False

        # We specifically use nodeload.github.com here because the download
        # URLs all redirect there, and some of the downloaders don't follow
        # HTTP redirect headers
        download_url = 'https://nodeload.github.com/' + \
            repo_info['owner']['login'] + '/' + \
            repo_info['name'] + '/zip/' + quote(branch)

        commit_date = commit_info[0]['commit']['committer']['date']
        timestamp = datetime.datetime.strptime(commit_date[0:19],
            '%Y-%m-%dT%H:%M:%S')
        utc_timestamp = timestamp.strftime(
            '%Y.%m.%d.%H.%M.%S')

        homepage = repo_info['homepage']
        if not homepage:
            homepage = repo_info['html_url']

        package = {
            'name': repo_info['name'],
            'description': repo_info['description'] if \
                repo_info['description'] else 'No description provided',
            'url': homepage,
            'author': repo_info['owner']['login'],
            'last_modified': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'downloads': [
                {
                    'version': utc_timestamp,
                    'url': download_url
                }
            ]
        }
        return {package['name']: package}

    def get_renamed_packages(self):
        """For API-compatibility with :class:`PackageProvider`"""

        return {}
