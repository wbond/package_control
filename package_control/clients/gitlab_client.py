import re
from urllib.parse import urlencode, quote

from ..downloaders.downloader_exception import DownloaderException
from ..package_version import version_match_prefix
from .json_api_client import JSONApiClient


class GitLabClient(JSONApiClient):

    @staticmethod
    def user_repo_branch(url):
        """
        Extract the username, repo and branch name from the URL

        :param url:
            The URL to extract the info from, in one of the forms:
              https://gitlab.com/{user}
              https://gitlab.com/{user}/{repo}
              https://gitlab.com/{user}/{repo}.git
              https://gitlab.com/{user}/{repo}/-/tree/{branch}

        :return:
            A tuple of
                (user name, repo name, branch name) or
                (user name, repo name, None) or
                (user name, None, None) or
                (None, None, None) if no match.

            The branch name may be a branch name or a commit
        """

        match = re.match(
            r'^https?://gitlab\.com/([^/#?]+)(?:/([^/#?]+?)(?:\.git|/-/tree/([^#?]*[^/#?])/?|/?)|/?)$',
            url
        )
        if match:
            return match.groups()

        return (None, None, None)

    @staticmethod
    def repo_url(user_name, repo_name):
        """
        Generate the tags URL for a GitLab repo if the value passed is a GitLab
        repository URL

        :param owener_name:
            The repository owner name

        :param repo_name:
            The repository name

        :return:
            The repository URL of given owner and repo name
        """

        return 'https://gitlab.com/%s/%s' % (quote(user_name), quote(repo_name))

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

        output = self.download_info_from_branch(url)
        if output is None:
            output = self.download_info_from_tags(url, tag_prefix)
        return output

    def download_info_from_branch(self, url, default_branch=None):
        """
        Retrieve information about downloading a package

        :param url:
            The URL of the repository, in one of the forms:
              https://gitlab.com/{user}/{repo}
              https://gitlab.com/{user}/{repo}/-/tree/{branch}

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

        repo_id = '%s%%2F%s' % (user_name, repo_name)

        if branch is None:
            branch = default_branch
            if branch is None:
                repo_info = self.fetch_json(self._api_url(repo_id))
                branch = repo_info.get('default_branch', 'master')

        branch_url = self._api_url(repo_id, '/repository/branches/%s' % branch)
        branch_info = self.fetch_json(branch_url)

        timestamp = branch_info['commit']['committed_date'][0:19].replace('T', ' ')
        version = re.sub(r'[\-: ]', '.', timestamp)

        return [self._make_download_info(user_name, repo_name, branch, version, timestamp)]

    def download_info_from_releases(self, url, asset_templates, tag_prefix=None):
        """
        Retrieve information about downloading a package

        :param url:
            The URL of the repository, in one of the forms:
              https://gitlab.com/{user}/{repo}
              https://gitlab.com/{user}/{repo}/-/releases
            Grabs the info from the newest tag(s) that is a valid semver version.

        :param tag_prefix:
            If the URL is a tags URL, only match tags that have this prefix.
            If tag_prefix is None, match only tags without prefix.

        :param asset_templates:
            A list of tuples of asset template and download_info.

            [
                (
                    "Name-${version}-st${st_build}-*-x??.sublime",
                    {
                        "platforms": ["windows-x64"],
                        "python_versions": ["3.3", "3.8"],
                        "sublime_text": ">=4107"
                    }
                )
            ]

            Supported globs:

              * : any number of characters
              ? : single character placeholder

            Supported variables are:

              ${platform}
                A platform-arch string as given in "platforms" list.
                A separate explicit release is evaluated for each platform.
                If "platforms": ['*'] is specified, variable is set to "any".

              ${py_version}
                Major and minor part of required python version without period.
                One of "33", "38" or any other valid python version supported by ST.

              ${st_build}
                Value of "st_specifier" stripped by leading operator
                  "*"            => "any"
                  ">=4107"       => "4107"
                  "<4107"        => "4107"
                  "4107 - 4126"  => "4107"

              ${version}
                Resolved semver without tag prefix
                (e.g.: tag st4107-1.0.5 => version 1.0.5)

                Note: is not replaced by this method, but by the ``ClientProvider``.

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            ``None`` if no match, ``False`` if no commit, or a list of dicts with the
            following keys:

              - `version` - the version number of the download
              - `url` - the download URL of a zip file of the package
              - `date` - the ISO-8601 timestamp string when the version was published
              - `platforms` - list of unicode strings with compatible platforms
              - `python_versions` - list of compatible python versions
              - `sublime_text` - sublime text version specifier

            Example:

            ```py
            [
                {
                  "url": "https://server.com/file.zip",
                  "version": "1.0.0",
                  "date": "2023-10-21 12:00:00",
                  "platforms": ["windows-x64"],
                  "python_versions": ["3.8"],
                  "sublime_text": ">=4107"
                },
                ...
            ]
            ```
        """

        match = re.match(r'https?://gitlab\.com/([^/#?]+)/([^/#?]+)(?:/-/releases)?/?$', url)
        if not match:
            return None

        def _get_releases(user_repo, tag_prefix=None, page_size=1000):
            used_versions = set()
            for page in range(10):
                query_string = urlencode({'page': page * page_size, 'per_page': page_size})
                api_url = self._api_url(user_repo, '/releases?%s' % query_string)
                releases = self.fetch_json(api_url)

                for release in releases:
                    version = version_match_prefix(release['tag_name'], tag_prefix)
                    if not version or version in used_versions:
                        continue

                    used_versions.add(version)

                    yield (
                        version,
                        release['released_at'][0:19].replace('T', ' '),
                        [
                            ((a['name'], a['direct_asset_url']))
                            for a in release['assets']['links']
                        ]
                    )

                if len(releases) < page_size:
                    return

        user_name, repo_name = match.groups()
        repo_id = '%s%%2F%s' % (user_name, repo_name)

        asset_templates = self._expand_asset_variables(asset_templates)

        max_releases = self.settings.get('max_releases', 0)
        num_releases = [0] * len(asset_templates)

        output = []

        for release in _get_releases(repo_id, tag_prefix):
            version, timestamp, assets = release

            version_string = str(version)

            for idx, (pattern, selectors) in enumerate(asset_templates):
                if max_releases > 0 and num_releases[idx] >= max_releases:
                    continue

                pattern = pattern.replace('${version}', version_string)
                pattern = pattern.replace('.', r'\.')
                pattern = pattern.replace('?', r'.')
                pattern = pattern.replace('*', r'.*?')
                regex = re.compile(pattern)

                for asset_name, asset_url in assets:
                    if not regex.match(asset_name):
                        continue

                    info = {'url': asset_url, 'version': version_string, 'date': timestamp}
                    info.update(selectors)
                    output.append(info)
                    num_releases[idx] += version.is_final
                    break

            if max_releases > 0 and min(num_releases) >= max_releases:
                break

        return output

    def download_info_from_tags(self, url, tag_prefix=None):
        """
        Retrieve information about downloading a package

        :param url:
            The URL of the repository, in one of the forms:
              https://gitlab.com/{user}/{repo}
              https://gitlab.com/{user}/{repo}/-/tags
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

        tags_match = re.match(r'https?://gitlab\.com/([^/#?]+)/([^/#?]+)(?:/-/tags)?/?$', url)
        if not tags_match:
            return None

        def _get_releases(repo_id, tag_prefix=None, page_size=1000):
            used_versions = set()
            for page in range(10):
                query_string = urlencode({'page': page * page_size, 'per_page': page_size})
                tags_url = self._api_url(repo_id, '/repository/tags?%s' % query_string)
                tags_json = self.fetch_json(tags_url)

                for tag in tags_json:
                    version = version_match_prefix(tag['name'], tag_prefix)
                    if version and version not in used_versions:
                        used_versions.add(version)
                        yield (
                            version,
                            tag['name'],
                            tag['commit']['committed_date'][0:19].replace('T', ' ')
                        )

                if len(tags_json) < page_size:
                    return

        user_name, repo_name = tags_match.groups()
        repo_id = '%s%%2F%s' % (user_name, repo_name)

        max_releases = self.settings.get('max_releases', 0)
        num_releases = 0

        output = []
        for release in sorted(_get_releases(repo_id, tag_prefix), reverse=True):
            version, tag, timestamp = release

            output.append(self._make_download_info(user_name, repo_name, tag, str(version), timestamp))

            num_releases += version.is_final
            if max_releases > 0 and num_releases >= max_releases:
                break

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
              `default_branch`
        """

        user_name, repo_name, branch = self.user_repo_branch(url)
        if not user_name or not repo_name:
            return None

        repo_id = '%s%%2F%s' % (user_name, repo_name)
        repo_url = self._api_url(repo_id)
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
              `default_branch`
        """

        user_match = re.match(r'https?://gitlab\.com/([^/#?]+)/?$', url)
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
              `default_branch`
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
            'default_branch': branch
        }

    def _make_download_info(self, user_name, repo_name, ref_name, version, timestamp):
        """
        Generate a download_info record

        :param user_name:
            The owner of the repository

        :param repo_name:
            The name of the repository

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
            'url': 'https://gitlab.com/%s/%s/-/archive/%s/%s-%s.zip' % (
                user_name, repo_name, ref_name, repo_name, ref_name),
            'version': version,
            'date': timestamp
        }

    def _api_url(self, project_id, suffix=''):
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
