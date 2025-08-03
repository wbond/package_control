import re
from urllib.parse import urlencode, quote

from ..downloaders.downloader_exception import DownloaderException
from ..package_version import version_match_prefix
from .json_api_client import JSONApiClient


# A predefined list of readme filenames to look for
_readme_filenames = [
    'readme',
    'readme.txt',
    'readme.md',
    'readme.mkd',
    'readme.mdown',
    'readme.markdown',
    'readme.textile',
    'readme.creole',
    'readme.rst'
]


class BitBucketClient(JSONApiClient):

    @staticmethod
    def user_repo_branch(url):
        """
        Extract the username, repo and branch name from the URL

        :param url:
            The URL to extract the info from, in one of the forms:
              https://bitbucket.org/{user}
              https://bitbucket.org/{user}/{repo}
              https://bitbucket.org/{user}/{repo}.git
              https://bitbucket.org/{user}/{repo}/src/{branch}

        :return:
            A tuple of
                (user name, repo name, branch name) or
                (user name, repo name, None) or
                (user name, None, None) or
                (None, None, None) if no match.
        """

        match = re.match(
            r'^https?://bitbucket\.org/([^/#?]+)(?:/([^/#?]+?)(?:\.git|/src/([^#?]*[^/#?])/?|/?)|/?)$',
            url
        )
        if match:
            return match.groups()

        return (None, None, None)

    @staticmethod
    def repo_url(user_name, repo_name):
        """
        Generate the tags URL for a GitHub repo if the value passed is a GitHub
        repository URL

        :param owener_name:
            The repository owner name

        :param repo_name:
            The repository name

        :return:
            The repository URL of given owner and repo name
        """

        return 'https://bitbucket.com/%s/%s' % (quote(user_name), quote(repo_name))

    def download_info(self, url, tag_prefix=None):
        """
        Retrieve information about downloading a package

        :param url:
            The URL of the repository, in one of the forms:
              https://bitbucket.org/{user}/{repo}
              https://bitbucket.org/{user}/{repo}/src/{branch}
              https://bitbucket.org/{user}/{repo}/#tags
            If the last option, grabs the info from the newest
            tag that is a valid semver version.

        :param tag_prefix:
            If the URL is a tags URL, only match tags that have this prefix.
            If tag_prefix is None, match only tags without prefix.

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            None if no match, False if no commit, or a list of dicts with the
            following keys:
              `version` - the version number of the download
              `url` - the download URL of a zip file of the package
              `date` - the ISO-8601 timestamp string when the version was published
        """

        output = self.download_info_from_branch(url)
        if output is None:
            output = self.download_info_from_tags(url, tag_prefix)
        return output

    def download_info_from_branch(self, url, default_branch=None):
        """
        Retrieve information about downloading a package

        :param url:
            The URL of the repository, in one of the forms:
              https://bitbucket.org/{user}/{repo}
              https://bitbucket.org/{user}/{repo}/src/{branch}

        :param default_branch:
            The branch to use, in case url is a repo url

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            None if no match, False if no commit, or a list of dicts with the
            following keys:
              `version` - the version number of the download
              `url` - the download URL of a zip file of the package
              `date` - the ISO-8601 timestamp string when the version was published
        """

        user_name, repo_name, branch = self.user_repo_branch(url)
        if not repo_name:
            return None

        user_repo = "%s/%s" % (user_name, repo_name)

        if branch is None:
            branch = default_branch
            if branch is None:
                repo_info = self.fetch_json(self._api_url(user_repo))
                branch = repo_info['mainbranch'].get('name', 'master')

        branch_url = self._api_url(user_repo, '/refs/branches/%s' % branch)
        branch_info = self.fetch_json(branch_url)

        timestamp = branch_info['target']['date'][0:19].replace('T', ' ')
        version = re.sub(r'[\-: ]', '.', timestamp)

        return [self._make_download_info(user_repo, branch, version, timestamp)]

    def download_info_from_releases(self, url, asset_templates, tag_prefix=None):
        """
        BitBucket doesn't support releases in ways GitHub/Gitlab do.

        It supports download assets, but those are not bound to tags or releases.

        Version information could be extracted from file names,
        but that's not how PC evaluates download assets, currently.
        """

        return None

    def download_info_from_tags(self, url, tag_prefix=None):
        """
        Retrieve information about downloading a package

        :param url:
            The URL of the repository, in one of the forms:
              https://bitbucket.org/{user}/{repo}
              https://bitbucket.org/{user}/{repo}/#tags
            Grabs the info from the newest tag(s) that is a valid semver version.

        :param tag_prefix:
            If the URL is a tags URL, only match tags that have this prefix.
            If tag_prefix is None, match only tags without prefix.

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            None if no match, False if no commit, or a list of dicts with the
            following keys:
              `version` - the version number of the download
              `url` - the download URL of a zip file of the package
              `date` - the ISO-8601 timestamp string when the version was published
        """

        tags_match = re.match(r'https?://bitbucket\.org/([^/#?]+/[^/#?]+)/?(?:#tags)?$', url)
        if not tags_match:
            return None

        def _get_releases(user_repo, tag_prefix, page_size=100):
            used_versions = set()
            query_string = urlencode({'pagelen': page_size})
            tags_url = self._api_url(user_repo, '/refs/tags?%s' % query_string)
            while tags_url:
                tags_json = self.fetch_json(tags_url)
                for tag in tags_json['values']:
                    version = version_match_prefix(tag['name'], tag_prefix)
                    if version and version not in used_versions:
                        used_versions.add(version)
                        yield (
                            version,
                            tag['name'],
                            tag['target']['date'][0:19].replace('T', ' ')
                        )

                tags_url = tags_json.get('next')

        user_repo = tags_match.group(1)

        max_releases = self.settings.get('max_releases', 0)
        num_releases = 0

        output = []
        for release in sorted(_get_releases(user_repo, tag_prefix), reverse=True):
            version, tag, timestamp = release

            output.append(self._make_download_info(user_repo, tag, str(version), timestamp))

            num_releases += version.is_final
            if max_releases > 0 and num_releases >= max_releases:
                break

        return output

    def repo_info(self, url):
        """
        Retrieve general information about a repository

        :param url:
            The URL to the repository, in one of the forms:
              https://bitbucket.org/{user}/{repo}
              https://bitbucket.org/{user}/{repo}/src/{branch}

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            None if no match, or a dict with the following keys:
              `name`
              `description`
              `homepage` - URL of the homepage
              `author`
              `readme` - URL of the readme
              `issues` - URL of bug tracker
              `donate` - URL of a donate page
              `default_branch`
        """

        user_name, repo_name, branch = self.user_repo_branch(url)
        if not repo_name:
            return None

        user_repo = "%s/%s" % (user_name, repo_name)
        api_url = self._api_url(user_repo)
        repo_info = self.fetch_json(api_url)

        if branch is None:
            branch = repo_info['mainbranch'].get('name', 'master')

        issues_url = 'https://bitbucket.org/%s/issues' % user_repo

        author = repo_info['owner'].get('nickname')
        if author is None:
            author = repo_info['owner'].get('username')

        is_client = self.settings.get('min_api_calls', False)
        readme_url = None if is_client else self._readme_url(user_repo, branch)

        return {
            'name': repo_info['name'],
            'description': repo_info['description'] or 'No description provided',
            'homepage': repo_info['website'] or url,
            'author': author,
            'donate': None,
            'readme': readme_url,
            'issues': issues_url if repo_info['has_issues'] else None,
            'default_branch': branch
        }

    def user_info(self, url):
        """
        For API compatibility with other clients.

        :param url:
            The URL to the repository, in one of the forms:
              https://bitbucket.org/{user}

        :return:
            None
        """
        return None

    def _make_download_info(self, user_repo, ref_name, version, timestamp):
        """
        Generate a download_info record

        :param user_repo:
            The user/repo of the repository

        :param ref_name:
            The git reference (branch, commit, tag)

        :param version:
            The prefixed version to add to the record

        :param timestamp:
            The timestamp the revision was created

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            A dictionary with following keys:
              `version` - the version number of the download
              `url` - the download URL of a zip file of the package
              `date` - the ISO-8601 timestamp string when the version was published
        """

        return {
            'url': 'https://bitbucket.org/%s/get/%s.zip' % (user_repo, ref_name),
            'version': version,
            'date': timestamp
        }

    def _api_url(self, user_repo, suffix=''):
        """
        Generate a URL for the BitBucket API

        :param user_repo:
            The user/repo of the repository

        :param suffix:
            The extra API path info to add to the URL

        :return:
            The API URL
        """

        return 'https://api.bitbucket.org/2.0/repositories/%s%s' % (user_repo, suffix)

    def _readme_url(self, user_repo, branch):
        """
        Parse the root directory listing for the repo and return the URL
        to any file that looks like a readme

        :param user_repo:
            The user/repo string

        :param branch:
            The branch to fetch the readme from

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            The URL to the readme file, or None
        """

        listing_url = self._api_url(user_repo, '/src/%s/?pagelen=100' % branch)

        try:
            while listing_url:
                root_dir_info = self.fetch_json(listing_url)

                for entry in root_dir_info['values']:
                    if entry['path'].lower() in _readme_filenames:
                        return 'https://bitbucket.org/%s/raw/%s/%s' % (user_repo, branch, entry['path'])

                listing_url = root_dir_info['next'] if 'next' in root_dir_info else None

        except (DownloaderException) as e:
            if 'HTTP error 404' not in str(e):
                raise

        return None
