import re
from urllib.parse import urlencode, quote

from ..versions import version_sort, version_process
from .json_api_client import JSONApiClient
from ..downloaders.downloader_exception import DownloaderException


class GitHubClient(JSONApiClient):

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

    @staticmethod
    def make_tags_url(repo_url):
        """
        Generate the tags URL for a GitHub repo if the value passed is a GitHub
        repository URL

        :param repo_url:
            The repository URL

        :return:
            The tags URL if repo was a GitHub repo_url, otherwise False
        """

        match = re.match('https?://github.com/([^/]+/[^/]+)/?$', repo_url)
        if not match:
            return False

        return 'https://github.com/%s/tags' % match.group(1)

    @staticmethod
    def make_branch_url(repo_url, branch):
        """
        Generate the branch URL for a GitHub repo if the value passed is a GitHub
        repository URL

        :param repo_url:
            The repository URL

        :param branch:
            The branch name

        :return:
            The branch URL if repo_url was a GitHub repo, otherwise False
        """

        match = re.match('https?://github.com/([^/]+/[^/]+)/?$', repo_url)
        if not match:
            return False

        return 'https://github.com/%s/tree/%s' % (match.group(1), quote(branch))

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
            If the URL is a tags URL, only match tags that have this prefix

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

        output = []

        version = None
        url_pattern = 'https://codeload.github.com/%s/zip/%s'

        # tag based releases
        tags_match = re.match('https?://github.com/([^/]+/[^/]+)/tags/?$', url)
        if tags_match:
            user_repo = tags_match.group(1)
            tags_url = self._make_api_url(user_repo, '/tags?per_page=100')
            tags_json = self.fetch_json(tags_url)
            tag_urls = {tag['name']: tag['commit']['url'] for tag in tags_json}
            tag_info = version_process(tag_urls.keys(), tag_prefix)
            tag_info = version_sort(tag_info, reverse=True)
            if not tag_info:
                return False

            used_versions = set()
            for info in tag_info:
                version = info['version']
                if version in used_versions:
                    continue

                tag = info['prefix'] + version
                tag_info = self.fetch_json(tag_urls[tag])
                timestamp = tag_info['commit']['committer']['date'][0:19].replace('T', ' ')

                output.append({
                    'url': url_pattern % (user_repo, tag),
                    'version': version,
                    'date': timestamp
                })
                used_versions.add(version)

        # branch based releases
        else:
            user_repo, branch = self._user_repo_branch(url)
            if not user_repo:
                return None

            if branch is None:
                repo_info = self.fetch_json(self._make_api_url(user_repo))
                branch = repo_info.get('default_branch', 'master')

            branch_url = self._make_api_url(user_repo, '/branches/%s' % branch)
            branch_info = self.fetch_json(branch_url)

            timestamp = branch_info['commit']['commit']['committer']['date'][0:19].replace('T', ' ')

            output = [{
                'url': url_pattern % (user_repo, branch),
                'version': re.sub(r'[\-: ]', '.', timestamp),
                'date': timestamp
            }]

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
        """

        user_repo, branch = self._user_repo_branch(url)
        if not user_repo:
            return user_repo

        api_url = self._make_api_url(user_repo)
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
        """

        user_match = re.match('https?://github.com/([^/]+)/?$', url)
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
            'donate': None
        }

    def _make_api_url(self, user_repo, suffix=''):
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
        readme_url = self._make_api_url(user_repo, '/readme?%s' % query_string)

        try:
            readme_file = self.fetch_json(readme_url, prefer_cached).get('path')
            if readme_file:
                return 'https://raw.githubusercontent.com/%s/%s/%s' % (user_repo, branch, readme_file)

        except (DownloaderException) as e:
            if 'HTTP error 404' not in str(e):
                raise

        return None

    def _user_repo_branch(self, url):
        """
        Extract the username/repo and branch name from the URL

        :param url:
            The URL to extract the info from, in one of the forms:
              https://github.com/{user}/{repo}
              https://github.com/{user}/{repo}/tree/{branch}

        :return:
            A tuple of (user/repo, branch name) or (None, None) if no match
        """

        branch_match = re.match('https?://github.com/([^/]+/[^/]+)/tree/([^/]+)/?$', url)
        if branch_match:
            return branch_match.groups()

        repo_match = re.match('https?://github.com/([^/]+/[^/]+)(?:$|/.*$)', url)
        if repo_match:
            return (repo_match.group(1), None)

        return (None, None)
