import re

from ..downloaders.downloader_exception import DownloaderException
from ..versions import version_process, version_sort
from .json_api_client import JSONApiClient

try:
    # Python 3
    from urllib.parse import urlencode, quote

    str_cls = str
except (ImportError):
    # Python 2
    from urllib import urlencode, quote

    str_cls = unicode  # noqa


class GitLabClient(JSONApiClient):
    def make_tags_url(self, repo):
        """
        Generate the tags URL for a GitLab repo if the value passed is a GitLab
        repository URL

        :param repo:
            The repository URL

        :return:
            The tags URL if repo was a GitLab repo, otherwise False
        """

        match = re.match('https?://gitlab.com/([^/]+/[^/]+)/?$', repo)
        if not match:
            return False

        return 'https://gitlab.com/%s/-/tags' % match.group(1)

    def make_branch_url(self, repo, branch):
        """
        Generate the branch URL for a GitLab repo if the value passed is a GitLab
        repository URL

        :param repo:
            The repository URL

        :param branch:
            The branch name

        :return:
            The branch URL if repo was a GitLab repo, otherwise False
        """

        match = re.match('https?://gitlab.com/([^/]+/[^/]+)/?$', repo)
        if not match:
            return False

        return 'https://gitlab.com/%s/-/tree/%s' % (match.group(1),
                                                    quote(branch))

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

        tags_match = re.match('https?://gitlab.com/([^/]+)/([^/]+)/-/tags/?$',
                              url)

        version = None
        url_pattern = 'https://gitlab.com/%s/-/archive/%s/%s-%s.zip'

        output = []
        if tags_match:
            (user_id, user_repo_type) = self._extract_user_id(tags_match.group(1))

            repo_id, _ = self._extract_repo_id_default_branch(
                user_id,
                tags_match.group(2),
                'users' if user_repo_type else 'groups'
            )
            if repo_id is None:
                return None

            user_repo = '%s/%s' % (tags_match.group(1), tags_match.group(2))
            tags_url = self._make_api_url(
                repo_id,
                '/repository/tags?per_page=100'
            )
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
                repo_name = user_repo.split('/')[1]
                output.append({
                    'url': url_pattern % (user_repo, tag, repo_name, tag),
                    'commit': tag,
                    'version': version,
                })
                used_versions[version] = True

        else:
            user_repo, commit = self._user_repo_ref(url)
            if not user_repo:
                return user_repo
            user, repo = user_repo.split('/')
            (user_id, user_repo_type) = self._extract_user_id(user)

            repo_id, default_branch = self._extract_repo_id_default_branch(
                user_id,
                repo,
                'users' if user_repo_type else 'groups'
            )
            if repo_id is None:
                return None

            if commit is None:
                commit = default_branch

            repo_name = user_repo.split('/')[1]
            output.append({
                'url': url_pattern % (user_repo, commit, repo_name, commit),
                'commit': commit
            })

        for release in output:
            query_string = urlencode({
                'ref_name': release['commit'],
                'per_page': 1
            })
            commit_url = self._make_api_url(
                repo_id,
                '/repository/commits?%s' % query_string
            )
            commit_info = self.fetch_json(commit_url)
            if not commit_info[0].get('commit'):
                timestamp = commit_info[0]['committed_date'][0:19].replace('T', ' ')
            else:
                timestamp = commit_info[0]['commit']['committed_date'][0:19].replace('T', ' ')

            if 'version' not in release:
                release['version'] = re.sub(r'[\-: ]', '.', timestamp)
            release['date'] = timestamp

            del release['commit']

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

        user_repo, branch = self._user_repo_ref(url)
        if not user_repo:
            return user_repo

        user, repo = user_repo.split('/')

        (user_id, user_repo_type) = self._extract_user_id(user)

        repo_id, default_branch = self._extract_repo_id_default_branch(
            user_id,
            repo,
            'users' if user_repo_type else 'groups'
        )
        if repo_id is None:
            return None

        if branch is None:
            branch = default_branch

        api_url = self._make_api_url(repo_id)
        info = self.fetch_json(api_url)

        output = self._extract_repo_info(info)

        if not output['readme']:
            return output

        output['readme'] = 'https://gitlab.com/%s/-/%s/%s' % (
            user_repo,
            branch,
            output['readme'].split('/')[-1],
        )
        return output

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
        (user_id, user_repo_type) = self._extract_user_id(user)

        api_url = 'https://gitlab.com/api/v4/%s/%s/projects' % (
            'users' if user_repo_type else 'groups', user_id)

        repos_info = self.fetch_json(api_url)

        output = []
        for info in repos_info:
            user_repo = '%s/%s' % (user, info['name'])
            branch = info['default_branch']

            repo_output = self._extract_repo_info(info)

            if repo_output['readme']:
                repo_output['readme'] = 'https://gitlab.com/%s/-/raw/%s/%s' % (
                    user_repo,
                    branch,
                    repo_output['readme'].split('/')[-1],
                )
            output.append(repo_output)
        return output

    def _extract_repo_info(self, result):
        """
        Extracts information about a repository from the API result

        :param result:
            A dict representing the data returned from the GitLab API

        :return:
            A dict with the following keys:
              `name`
              `description`
              `homepage` - URL of the homepage
              `author`
              `issues` - URL of bug tracker
              `donate` - URL of a donate page
        """

        return {
            'name': result['name'],
            'description': result['description'] or 'No description provided',
            'homepage': result['web_url'] or None,
            'readme': result['readme_url'] if result['readme_url'] else None,
            'author': result['owner']['username'] if result.get('owner') else result['namespace']['name'],
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

    def _user_repo_ref(self, url):
        """
        Extract the username/repo and ref name from the URL

        :param url:
            The URL to extract the info from, in one of the forms:
              https://gitlab.com/{user}/{repo}
              https://gitlab.com/{user}/{repo}/-/tree/{ref}

        :return:
            A tuple of (user/repo, ref name) or (None, None) if no match.
            The ref name may be a branch name or a commit
        """

        branch = None
        branch_match = re.match(
            r'https?://gitlab.com/[^/]+/[^/]+/-/tree/([^/]+)/?$',
            url
        )
        if branch_match is not None:
            branch = branch_match.group(1)

        repo_match = re.match(
            r'https?://gitlab.com/([^/]+/[^/]+)($|/.*$)',
            url
        )
        if repo_match is None:
            return (None, None)

        user_repo = repo_match.group(1)
        return (user_repo, branch)

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
            if str_cls(e).find('HTTP error 404') != -1:
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
            if str_cls(e).find('HTTP error 404') != -1:
                return (None, None)
            raise

        if not repos_info:
            return (None, None)

        return (repos_info[0]['id'], False)

    def _extract_repo_id_default_branch(self, user_id, repo_name, repo_type):
        """
        Extract the repo id from the repo results

        :param user_id:
            The user_id of the user who owns the repo

        :param repo_name:
            The name of the repository

        :param repo_type:
            A string "users" or "groups", based on the user_id being from a
            user or a group

        :return:
            A 2-element tuple, (repo_id, default_branch) or (None, None) if no match
        """

        user_url = 'https://gitlab.com/api/v4/%s/%s/projects' % (repo_type, user_id)
        try:
            repos_info = self.fetch_json(user_url)
        except (DownloaderException) as e:
            if str_cls(e).find('HTTP error 404') != -1:
                return (None, None)
            raise

        repo_info = next(
            (repo for repo in repos_info if repo['name'].lower() == repo_name.lower()), None)

        if not repo_info:
            return (None, None)

        return (repo_info['id'], repo_info['default_branch'])
