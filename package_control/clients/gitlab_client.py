import re
from urllib.parse import quote

from ..downloaders.downloader_exception import DownloaderException
from ..versions import version_process, version_sort
from .json_api_client import JSONApiClient


class GitLabClient(JSONApiClient):

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

        return 'https://gitlab.com/%s/%s' % (quote(owner_name), quote(repo_name))

    @staticmethod
    def make_tags_url(repo_url):
        """
        Generate the tags URL for a GitLab repo if the value passed is a GitLab
        repository URL

        :param repo_url:
            The repository URL

        :return:
            The tags URL if repo_url was a GitLab repo, otherwise False
        """

        match = re.match('https?://gitlab.com/([^/]+/[^/]+)/?$', repo_url)
        if not match:
            return False

        return 'https://gitlab.com/%s/-/tags' % match.group(1)

    @staticmethod
    def make_branch_url(repo_url, branch):
        """
        Generate the branch URL for a GitLab repo if the value passed is a GitLab
        repository URL

        :param repo_url:
            The repository URL

        :param branch:
            The branch name

        :return:
            The branch URL if repo_url was a GitLab repo, otherwise False
        """

        match = re.match('https?://gitlab.com/([^/]+/[^/]+)/?$', repo_url)
        if not match:
            return False

        return 'https://gitlab.com/%s/-/tree/%s' % (match.group(1), quote(branch))

    def download_info(self, url, tag_prefix=None):
        """
        Retrieve information about downloading a package

        :param url:
            The URL of the repository, in one of the forms:
              https://gitlab.com/{user}/{repo}
              https://gitlab.com/{user}/{repo}/-/tree/{branch}
              https://gitlab.com/{user}/{repo}/-/tags
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

        output = []

        version = None
        url_pattern = 'https://gitlab.com/%s/%s/-/archive/%s/%s-%s.zip'

        # tag based releases
        tags_match = re.match('https?://gitlab.com/([^/]+)/([^/]+)/-/tags/?$', url)
        if tags_match:
            user_name, repo_name = tags_match.groups()
            repo_id = '%s%%2F%s' % (user_name, repo_name)
            tags_url = self._make_api_url(repo_id, '/repository/tags?per_page=100')
            tags_json = self.fetch_json(tags_url)
            tags_list = {
                tag['name']: tag['commit']['committed_date'][0:19].replace('T', ' ')
                for tag in tags_json
            }

            tag_info = version_process(tags_list.keys(), tag_prefix)
            tag_info = version_sort(tag_info, reverse=True)
            if not tag_info:
                return False

            max_releases = self.settings.get('max_releases', 0)

            used_versions = set()
            for info in tag_info:
                version = info['version']
                if version in used_versions:
                    continue

                tag = info['prefix'] + version
                output.append({
                    'url': url_pattern % (user_name, repo_name, tag, repo_name, tag),
                    'version': version,
                    'date': tags_list[tag]
                })
                used_versions.add(version)
                if max_releases > 0 and len(used_versions) >= max_releases:
                    break

        # branch based releases
        else:
            user_repo, branch = self._user_repo_branch(url)
            if not user_repo:
                return None

            user_name, repo_name = user_repo.split('/')
            repo_id = '%s%%2F%s' % (user_name, repo_name)

            if branch is None:
                repo_info = self.fetch_json(self._make_api_url(repo_id))
                branch = repo_info.get('default_branch', 'master')

            branch_url = self._make_api_url(repo_id, '/repository/branches/%s' % branch)
            branch_info = self.fetch_json(branch_url)

            timestamp = branch_info['commit']['committed_date'][0:19].replace('T', ' ')

            output = [{
                'url': url_pattern % (user_name, repo_name, branch, repo_name, branch),
                'version': re.sub(r'[\-: ]', '.', timestamp),
                'date': timestamp
            }]

        return output

    def repo_info(self, url):
        """
        Retrieve general information about a repository
        :param url:
            The URL to the repository, in one of the forms:
              https://gitlab.com/{user}/{repo}
              https://gitlab.com/{user}/{repo}/-/tree/{branch}
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
            return None

        user_name, repo_name = user_repo.split('/')
        repo_id = '%s%%2F%s' % (user_name, repo_name)
        repo_url = self._make_api_url(repo_id)
        repo_info = self.fetch_json(repo_url)

        if not branch:
            branch = repo_info.get('default_branch', 'master')

        return self._extract_repo_info(branch, repo_info)

    def user_info(self, url):
        """
        Retrieve general information about all repositories that are
        part of a user/organization.

        :param url:
            The URL to the user/organization, in the following form:
              https://gitlab.com/{user}

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

        user_match = re.match('https?://gitlab.com/([^/]+)/?$', url)
        if user_match is None:
            return None

        user = user_match.group(1)
        user_id, user_repo_type = self._extract_user_id(user)

        api_url = 'https://gitlab.com/api/v4/%s/%s/projects' % (
            'users' if user_repo_type else 'groups', user_id)

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
            A dict representing the data returned from the GitLab API

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

        user_name = result['owner']['username'] if result.get('owner') else result['namespace']['name']
        repo_name = result['name']
        user_repo = '%s/%s' % (user_name, repo_name)

        readme_url = None
        if result['readme_url']:
            readme_url = 'https://gitlab.com/%s/-/raw/%s/%s' % (
                user_repo, branch, result['readme_url'].split('/')[-1]
            )

        return {
            'name': repo_name,
            'description': result['description'] or 'No description provided',
            'homepage': result['web_url'] or None,
            'author': user_name,
            'readme': readme_url,
            'issues': result.get('issues', None) if result.get('_links') else None,
            'donate': None,
        }

    def _make_api_url(self, project_id, suffix=''):
        """
        Generate a URL for the GitLab API

        :param user_repo:
            The user/repo of the repository

        :param suffix:
            The extra API path info to add to the URL

        :return:
            The API URL
        """

        return 'https://gitlab.com/api/v4/projects/%s%s' % (project_id, suffix)

    def _user_repo_branch(self, url):
        """
        Extract the username/repo and branch name from the URL

        :param url:
            The URL to extract the info from, in one of the forms:
              https://gitlab.com/{user}/{repo}
              https://gitlab.com/{user}/{repo}/-/tree/{branch}

        :return:
            A tuple of (user/repo, branch name) or (None, None) if no match.
            The branch name may be a branch name or a commit
        """

        branch_match = re.match('https?://gitlab.com/([^/]+/[^/]+)/-/tree/([^/]+)/?$', url)
        if branch_match:
            return branch_match.groups()

        repo_match = re.match('https?://gitlab.com/([^/]+/[^/]+)(?:$|/.*$)', url)
        if repo_match:
            return (repo_match.group(1), None)

        return (None, None)

    def _extract_user_id(self, username):
        """
        Extract the user id from the repo results

        :param username:
            The username to extract the user_id from

        :return:
            A user_id or None if no match
        """

        user_url = 'https://gitlab.com/api/v4/users?username=%s' % username
        try:
            repos_info = self.fetch_json(user_url)
        except (DownloaderException) as e:
            if str(e).find('HTTP error 404') != -1:
                return self._extract_group_id(username)
            raise

        if not repos_info:
            return self._extract_group_id(username)

        return (repos_info[0]['id'], True)

    def _extract_group_id(self, group_name):
        """
        Extract the group id from the repo results

        :param group:
            The group to extract the user_id from

        :return:
            A group_id or (None, None) if no match
        """

        group_url = 'https://gitlab.com/api/v4/groups?search=%s' % group_name
        try:
            repos_info = self.fetch_json(group_url)
        except (DownloaderException) as e:
            if str(e).find('HTTP error 404') != -1:
                return (None, None)
            raise

        if not repos_info:
            return (None, None)

        return (repos_info[0]['id'], False)
