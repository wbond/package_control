import re

try:
    # Python 3
    from urllib.parse import urlencode, quote
except (ImportError):
    # Python 2
    from urllib import urlencode, quote

from ..versions import version_sort, version_process
from .json_api_client import JSONApiClient
from ..downloaders.downloader_exception import DownloaderException


class GitHubClient(JSONApiClient):

    def make_tags_url(self, repo):
        """
        Generate the tags URL for a GitHub repo if the value passed is a GitHub
        repository URL

        :param repo:
            The repository URL

        :return:
            The tags URL if repo was a GitHub repo, otherwise False
        """

        match = re.match('https?://github.com/([^/]+/[^/]+)/?$', repo)
        if not match:
            return False

        return 'https://github.com/%s/tags' % match.group(1)

    def make_branch_url(self, repo, branch):
        """
        Generate the branch URL for a GitHub repo if the value passed is a GitHub
        repository URL

        :param repo:
            The repository URL

        :param branch:
            The branch name

        :return:
            The branch URL if repo was a GitHub repo, otherwise False
        """

        match = re.match('https?://github.com/([^/]+/[^/]+)/?$', repo)
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

        tags_match = re.match('https?://github.com/([^/]+/[^/]+)/tags/?$', url)

        version = None
        url_pattern = 'https://codeload.github.com/%s/zip/%s'

        output = []
        if tags_match:
            user_repo = tags_match.group(1)
            tags_url = self._make_api_url(user_repo, '/tags')
            tags_list = self.fetch_json(tags_url)
            tags = [tag['name'] for tag in tags_list]
            tag_info = version_process(tags, tag_prefix)
            tag_info = version_sort(tag_info, reverse=True)
            if not tag_info:
                return False

            used_versions = {}
            for info in tag_info:
                version = info['version']
                if version in used_versions:
                    continue
                tag = info['prefix'] + version
                output.append({
                    'url': url_pattern % (user_repo, tag),
                    'commit': tag,
                    'version': version
                })
                used_versions[version] = True

        else:
            user_repo, commit = self._user_repo_branch(url)
            if not user_repo:
                return user_repo

            output.append({
                'url': url_pattern % (user_repo, commit),
                'commit': commit
            })

        for release in output:
            query_string = urlencode({'sha': release['commit'], 'per_page': 1})
            commit_url = self._make_api_url(user_repo, '/commits?%s' % query_string)
            commit_info = self.fetch_json(commit_url)

            timestamp = commit_info[0]['commit']['committer']['date'][0:19].replace('T', ' ')

            if 'version' not in release:
                release['version'] = re.sub('[\-: ]', '.', timestamp)
            release['date'] = timestamp

            del release['commit']

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

        info = self.fetch_json(api_url)

        output = self._extract_repo_info(info)
        output['readme'] = None

        readme_info = self._readme_info(user_repo, branch)
        if not readme_info:
            return output

        output['readme'] = 'https://raw.githubusercontent.com/%s/%s/%s' % (
            user_repo, branch, readme_info['path'])
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
        api_url = 'https://api.github.com/users/%s/repos' % user

        repos_info = self.fetch_json(api_url)

        output = []
        for info in repos_info:
            user_repo = '%s/%s' % (user, info['name'])
            branch = 'master'

            repo_output = self._extract_repo_info(info)
            repo_output['readme'] = None

            readme_info = self._readme_info(user_repo, branch)
            if readme_info:
                repo_output['readme'] = 'https://raw.githubusercontent.com/%s/%s/%s' % (
                    user_repo, branch, readme_info['path'])

            output.append(repo_output)
        return output

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
            'donate': u'https://gratipay.com/on/github/%s/' % result['owner']['login']
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
