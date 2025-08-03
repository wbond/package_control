import re
from urllib.parse import urlencode, quote

from ..downloaders.downloader_exception import DownloaderException
from ..package_version import version_match_prefix
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
        match = re.match(
            r'^https?://github\.com/([^/#?]+)(?:/([^/#?]+?)(?:\.git|/tree/([^#?]*[^/#?])/?|/?)|/?)$',
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

        return 'https://github.com/%s/%s' % (quote(user_name), quote(repo_name))

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
                branch = repo_info.get('default_branch', 'master')

        branch_url = self._api_url(user_repo, '/branches/%s' % branch)
        branch_info = self.fetch_json(branch_url)

        timestamp = branch_info['commit']['commit']['committer']['date'][0:19].replace('T', ' ')
        version = re.sub(r'[\-: ]', '.', timestamp)

        return [self._make_download_info(user_repo, branch, version, timestamp)]

    def download_info_from_releases(self, url, asset_templates, tag_prefix=None):
        """
        Retrieve information about downloading a package

        :param url:
            The URL of the repository, in one of the forms:
              https://github.com/{user}/{repo}
              https://github.com/{user}/{repo}/releases
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

        match = re.match(r'https?://github\.com/([^/#?]+/[^/#?]+)(?:/releases)?/?$', url)
        if not match:
            return None

        def _get_releases(user_repo, tag_prefix=None, page_size=1000):
            used_versions = set()
            for page in range(10):
                query_string = urlencode({'page': page * page_size, 'per_page': page_size})
                api_url = self._api_url(user_repo, '/releases?%s' % query_string)
                releases = self.fetch_json(api_url)

                for release in releases:
                    if release['draft']:
                        continue
                    version = version_match_prefix(release['tag_name'], tag_prefix)
                    if not version or version in used_versions:
                        continue

                    used_versions.add(version)

                    yield (
                        version,
                        release['published_at'][0:19].replace('T', ' '),
                        [
                            (
                                a['label'] or a['browser_download_url'].rpartition("/")[-1],
                                a['browser_download_url']
                            )
                            for a in release['assets']
                            if a['state'] == 'uploaded'
                        ]
                    )

                if len(releases) < page_size:
                    return

        asset_templates = self._expand_asset_variables(asset_templates)

        user_repo = match.group(1)
        max_releases = self.settings.get('max_releases', 0)
        num_releases = [0] * len(asset_templates)

        output = []

        for release in _get_releases(user_repo, tag_prefix):
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

        def _get_releases(user_repo, tag_prefix=None, page_size=1000):
            used_versions = set()
            for page in range(10):
                query_string = urlencode({'page': page * page_size, 'per_page': page_size})
                tags_url = self._api_url(user_repo, '/tags?%s' % query_string)
                tags_json = self.fetch_json(tags_url)

                for tag in tags_json:
                    version = version_match_prefix(tag['name'], tag_prefix)
                    if version and version not in used_versions:
                        used_versions.add(version)
                        yield (version, tag['name'], tag['commit']['url'])

                if len(tags_json) < page_size:
                    return

        user_repo = tags_match.group(1)
        is_client = self.settings.get('min_api_calls', False)
        max_releases = self.settings.get('max_releases', 0)
        num_releases = 0

        output = []
        for release in sorted(_get_releases(user_repo, tag_prefix), reverse=True):
            version, tag, tag_url = release

            if is_client:
                timestamp = '1970-01-01 00:00:00'
            else:
                tag_info = self.fetch_json(tag_url)
                timestamp = tag_info['commit']['committer']['date'][0:19].replace('T', ' ')

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

    def _readme_url(self, user_repo, branch):
        """
        Fetches the raw GitHub API information about a readme

        :param user_repo:
            The user/repo of the repository

        :param branch:
            The branch to pull the readme from

        :raises:
            DownloaderException: when there is an error downloading
            ClientException: when there is an error parsing the response

        :return:
            A dict containing all of the info from the GitHub API, or None if no readme exists
        """

        query_string = urlencode({'ref': branch})
        readme_url = self._api_url(user_repo, '/readme?%s' % query_string)

        try:
            readme_file = self.fetch_json(readme_url).get('path')
            if readme_file:
                return 'https://raw.githubusercontent.com/%s/%s/%s' % (user_repo, branch, readme_file)

        except (DownloaderException) as e:
            if 'HTTP error 404' not in str(e):
                raise

        return None
