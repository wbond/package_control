import re

try:
    # Python 3
    from urllib.parse import urlencode, quote
except (ImportError):
    # Python 2
    from urllib import urlencode, quote

from ..versions import version_sort, version_filter
from .json_api_client import JSONApiClient
from ..downloaders.downloader_exception import DownloaderException


class GitHubClient(JSONApiClient):

    def download_info(self, url):
        """
        Retrieve information about downloading a package

        :param url:
            The URL of the repository, in one of the forms:
              https://github.com/{user}/{repo}
              https://github.com/{user}/{repo}/tree/{branch}
              https://github.com/{user}/{repo}/tags
            If the last option, grabs the info from the newest
            tag that is a valid semver version.

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            None if no match, False if no commit, or a dict with the following keys:
              `version` - the version number of the download
              `url` - the download URL of a zip file of the package
              `date` - the ISO-8601 timestamp string when the version was published
        """

        commit_info = self._commit_info(url)
        if not commit_info:
            return commit_info

        commit_date = commit_info['timestamp'][0:19].replace('T', ' ')

        return {
            'version': re.sub('[\-: ]', '.', commit_date),
            # We specifically use codeload.github.com here because the download
            # URLs all redirect there, and some of the downloaders don't follow
            # HTTP redirect headers
            'url': 'https://codeload.github.com/%s/zip/%s' % (commit_info['user_repo'], quote(commit_info['commit'])),
            'date': commit_date
        }

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

        info = self.fetch_json(api_url)

        output = self._extract_repo_info(info)
        output['readme'] = None

        readme_info = self._readme_info(user_repo, branch)
        if not readme_info:
            return output

        output['readme'] = 'https://raw.github.com/%s/%s/%s' % (user_repo,
            branch, readme_info['path'])
        return output

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
        if user_match == None:
            return None

        user = user_match.group(1)
        api_url = self._make_api_url(user)

        repos_info = self.fetch_json(api_url)

        output = []
        for info in repos_info:
            output.append(self._extract_repo_info(info))
        return output

    def _commit_info(self, url):
        """
        Fetches info about the latest commit to a repository

        :param url:
            The URL to the repository, in one of the forms:
              https://github.com/{user}/{repo}
              https://github.com/{user}/{repo}/tree/{branch}
              https://github.com/{user}/{repo}/tags
            If the last option, grabs the info from the newest
            tag that is a valid semver version.

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            None if no match, False is no commit, or a dict with the following keys:
              `user_repo` - the user/repo name
              `timestamp` - the ISO-8601 UTC timestamp string
              `commit` - the branch or tag name
        """

        tags_match = re.match('https?://github.com/([^/]+/[^/]+)/tags/?$', url)

        if tags_match:
            user_repo = tags_match.group(1)
            tags_url = self._make_api_url(user_repo, '/tags')
            tags_list = self.fetch_json(tags_url)
            tags = [tag['name'] for tag in tags_list]
            tags = version_filter(tags, self.settings.get('install_prereleases'))
            tags = version_sort(tags, reverse=True)
            if not tags:
                return False
            commit = tags[0]

        else:
            user_repo, commit = self._user_repo_branch(url)
            if not user_repo:
                return user_repo

        query_string = urlencode({'sha': commit, 'per_page': 1})
        commit_url = self._make_api_url(user_repo, '/commits?%s' % query_string)
        commit_info = self.fetch_json(commit_url)

        return {
            'user_repo': user_repo,
            'timestamp': commit_info[0]['commit']['committer']['date'],
            'commit': commit
        }

    def _extract_repo_info(self, result):
        """
        Extracts information about a repository from the API result

        :param result:
            A dict representing the data returned from the GitHub API

        :return:
            A dict with the following keys:
              `name`
              `description`
              `homepage` - URL of the homepage
              `author`
              `issues` - URL of bug tracker
              `donate` - URL of a donate page
        """

        issues_url = u'https://github.com/%s/%s/issues' % (result['owner']['login'], result['name'])

        return {
            'name': result['name'],
            'description': result['description'] or 'No description provided',
            'homepage': result['homepage'] or result['html_url'],
            'author': result['owner']['login'],
            'issues': issues_url if result['has_issues'] else None,
            'donate': u'https://www.gittip.com/on/github/%s/' % result['owner']['login']
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

    def _readme_info(self, user_repo, branch, prefer_cached=False):
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
            return self.fetch_json(readme_url, prefer_cached)
        except (DownloaderException) as e:
            if str(e).find('HTTP error 404') != -1:
                return None
            raise

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

        branch = 'master'
        branch_match = re.match('https?://github.com/[^/]+/[^/]+/tree/([^/]+)/?$', url)
        if branch_match != None:
            branch = branch_match.group(1)

        repo_match = re.match('https?://github.com/([^/]+/[^/]+)($|/.*$)', url)
        if repo_match == None:
            return (None, None)

        user_repo = repo_match.group(1)
        return (user_repo, branch)
