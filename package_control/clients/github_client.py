import re
from urllib.parse import urlencode, quote

from ..downloaders.downloader_exception import DownloaderException
from ..versions import version_sort, version_process
from .json_api_client import JSONApiClient


class GitHubClient(JSONApiClient):

    @staticmethod
    def user_repo_branch(url):
        """
        Extract the username, repo and branch name from the URL

        :param url:
            The URL to extract the info from, in one of the forms:
              https://github.com/{user}
              https://github.com/{user}/{repo}
              https://github.com/{user}/{repo}.git
              https://github.com/{user}/{repo}/tree/{branch}

        :return:
            A tuple of
                (user name, repo name, branch name) or
                (user name, repo name, None) or
                (user name, None, None) or
                (None, None, None) if no match.
        """
        match = re.match(r'^https?://github\.com/([^/#?]+)(?:/([^/#?]+?)(?:\.git|/tree/([^/#?]+)/?|/?)|/?)$', url)
        if match:
            return match.groups()

        return (None, None, None)

    @staticmethod
    def make_repo_url(owner_name, repo_name):
        """
        Generate the tags URL for a GitHub repo if the value passed is a GitHub
        repository URL

        :param owener_name:
            The repository owner name

        :param repo_name:
            The repository name

        :return:
            The repositoy URL of given owner and repo name
        """

        return 'https://github.com/%s/%s' % (quote(owner_name), quote(repo_name))

    def download_info(self, url, tag_prefix=None):
        """
        Retrieve information about downloading a package

        :param url:
            The URL of the repository, in one of the forms:
              https://github.com/{user}/{repo}
              https://github.com/{user}/{repo}/tree/{branch}
              https://github.com/{user}/{repo}/tags
            If the last option, grabs the info from the newest
            tag that is a valid semver version.

        :param tag_prefix:
            If the URL is a tags URL, only match tags that have this prefix.
            If tag_prefix is None, match only tags without prefix.

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            None if no match, False if no commits, or a list of dicts with the
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
              https://github.com/{user}/{repo}
              https://github.com/{user}/{repo}/tree/{branch}

        :param default_branch:
            The branch to use, in case url is a repo url

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            None if no match or a dict with the following keys:
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
                branch = repo_info.get('default_branch', 'master')

        branch_url = self._api_url(user_repo, '/branches/%s' % branch)
        branch_info = self.fetch_json(branch_url)

        timestamp = branch_info['commit']['commit']['committer']['date'][0:19].replace('T', ' ')
        version = re.sub(r'[\-: ]', '.', timestamp)

        return [self._make_download_info(user_repo, branch, version, timestamp)]

    def download_info_from_tags(self, url, tag_prefix=None):
        """
        Retrieve information about downloading a package

        :param url:
            The URL of the repository, in one of the forms:
              https://github.com/{user}/{repo}
              https://github.com/{user}/{repo}/tags
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

        tags_match = re.match(r'https?://github\.com/([^/#?]+/[^/#?]+)(?:/tags)?/?$', url)
        if not tags_match:
            return None

        user_repo = tags_match.group(1)
        tags_url = self._api_url(user_repo, '/tags?per_page=100')
        tags_json = self.fetch_json(tags_url)
        tag_urls = {tag['name']: tag['commit']['url'] for tag in tags_json}
        tag_info = version_process(tag_urls.keys(), tag_prefix)
        tag_info = version_sort(tag_info, reverse=True)
        if not tag_info:
            return False

        max_releases = self.settings.get('max_releases', 0)

        output = []
        used_versions = set()
        for info in tag_info:
            version = info['version']
            if version in used_versions:
                continue

            tag = info['prefix'] + version
            tag_info = self.fetch_json(tag_urls[tag])
            timestamp = tag_info['commit']['committer']['date'][0:19].replace('T', ' ')

            output.append(self._make_download_info(user_repo, tag, version, timestamp))

            used_versions.add(version)
            if max_releases > 0 and len(used_versions) >= max_releases:
                break

        return output

    def repo_info(self, url):
        """
        Retrieve general information about a repository

        :param url:
            The URL to the repository, in one of the forms:
              https://github.com/{user}/{repo}
              https://github.com/{user}/{repo}/tree/{branch}

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
            branch = repo_info.get('default_branch', 'master')

        return self._extract_repo_info(branch, repo_info)

    def user_info(self, url):
        """
        Retrieve general information about all repositories that are
        part of a user/organization.

        :param url:
            The URL to the user/organization, in the following form:
              https://github.com/{user}

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            None if no match, or am list of dicts with the following keys:
              `name`
              `description`
              `homepage` - URL of the homepage
              `author`
              `readme` - URL of the readme
              `issues` - URL of bug tracker
              `donate` - URL of a donate page
              `default_branch`
        """

        user_match = re.match(r'https?://github\.com/([^/#?]+)/?$', url)
        if user_match is None:
            return None

        user = user_match.group(1)
        api_url = 'https://api.github.com/users/%s/repos' % user

        repos_info = self.fetch_json(api_url)

        return [
            self._extract_repo_info(info.get('default_branch', 'master'), info)
            for info in repos_info
        ]

    def _extract_repo_info(self, branch, result):
        """
        Extracts information about a repository from the API result

        :param branch:
            The branch to return data from

        :param result:
            A dict representing the data returned from the GitHub API

        :return:
            A dict with the following keys:
              `name`
              `description`
              `homepage` - URL of the homepage
              `author`
              `readme` - URL of the homepage
              `issues` - URL of bug tracker
              `donate` - URL of a donate page
              `default_branch`
        """

        user_name = result['owner']['login']
        repo_name = result['name']
        user_repo = '%s/%s' % (user_name, repo_name)

        issues_url = None
        if result['has_issues']:
            issues_url = 'https://github.com/%s/issues' % user_repo

        return {
            'name': repo_name,
            'description': result['description'] or 'No description provided',
            'homepage': result['homepage'] or result['html_url'],
            'author': user_name,
            'readme': self._readme_url(user_repo, branch),
            'issues': issues_url,
            'donate': None,
            'default_branch': branch
        }

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
            'url': 'https://codeload.github.com/%s/zip/%s' % (user_repo, ref_name),
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

        return 'https://api.github.com/repos/%s%s' % (user_repo, suffix)

    def _readme_url(self, user_repo, branch, prefer_cached=False):
        """
        Fetches the raw GitHub API information about a readme

        :param user_repo:
            The user/repo of the repository

        :param branch:
            The branch to pull the readme from

        :param prefer_cached:
            If a cached version of the info should be returned instead of making a new HTTP request

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            A dict containing all of the info from the GitHub API, or None if no readme exists
        """

        query_string = urlencode({'ref': branch})
        readme_url = self._api_url(user_repo, '/readme?%s' % query_string)

        try:
            readme_file = self.fetch_json(readme_url, prefer_cached).get('path')
            if readme_file:
                return 'https://raw.githubusercontent.com/%s/%s/%s' % (user_repo, branch, readme_file)

        except (DownloaderException) as e:
            if 'HTTP error 404' not in str(e):
                raise

        return None
