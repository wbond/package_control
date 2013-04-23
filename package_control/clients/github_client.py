import re

try:
    # Python 3
    from urllib.parse import urlencode, quote
except (ImportError):
    # Python 2
    from urllib import urlencode, quote

from ..versions import version_sort, version_filter
from .json_api_client import JSONApiClient


class GitHubClient(JSONApiClient):
    def repo_info(self, url):
        branch = 'master'
        branch_match = re.match('https?://github.com/[^/]+/[^/]+/tree/([^/]+)/?$', url)
        if branch_match != None:
            branch = branch_match.group(1)

        repo_match = re.match('https?://github.com/([^/]+/[^/]+)($|/.*$)', url)
        if repo_match == None:
            return False

        user_repo = repo_match.group(1)
        api_url = self.make_api_url(user_repo)

        info = self.fetch_json(api_url)
        if not info:
            return info

        output = self.extract_repo_info(info)
        output['readme'] = None

        query_string = urlencode({'ref': branch})
        readme_url = self.make_api_url(user_repo, '/readme?%s' % query_string)
        readme_info = self.fetch_json(readme_url)
        if not readme_info:
            return output

        output['readme'] = 'https://raw.github.com/%s/%s/%s' % (user_repo,
            branch, readme_info['path'])
        return output

    def user_info(self, url):
        user_match = re.match('https?://github.com/([^/]+)/?$', url)
        if user_match == None:
            return False

        user = user_match.group(1)
        api_url = self.make_api_url(user)

        repos_info = self.fetch_json(api_url)
        if not repos_info:
            return repos_info

        output = []
        for info in repos_info:
            output.append(self.extract_repo_info(info))
        return output

    def extract_repo_info(self, result):
        return {
            'name': result['name'],
            'description': result['description'] or 'No description provided',
            'homepage': result['homepage'] or result['html_url'],
            'author': result['owner']['login'],
            'donate': u'https://www.gittip.com/%s/' % result['owner']['login']
        }

    def commit_info(self, url):
        repo_match = re.match('https?://github.com/([^/]+/[^/]+)/?$', url)
        branch_match = re.match('https?://github.com/([^/]+/[^/]+)/tree/([^/]+)/?$', url)
        tags_match = re.match('https?://github.com/([^/]+/[^/]+)/tags/?$', url)

        if repo_match:
            user_repo = repo_match.group(1)
            commit = 'master'

        elif branch_match:
            user_repo = branch_match.group(1)
            commit = branch_match.group(2)

        elif tags_match:
            user_repo = tags_match.group(1)
            tags_url = self.make_api_url(user_repo, '/tags')
            tags_list = self.fetch_json(tags_url)
            if tags_list == False:
                return False
            tags = version_filter([tag['name'] for tag in tags_list])
            tags = version_sort(tags, reverse=True)
            commit = tags[0]

        else:
            return False

        query_string = urlencode({'sha': commit, 'per_page': 1})
        commit_url = self.make_api_url(user_repo, '/commits?%s' % query_string)
        commit_info = self.fetch_json(commit_url)
        if commit_info == False:
            return False

        return {
            'user_repo': user_repo,
            'timestamp': commit_info[0]['commit']['committer']['date'],
            'commit': commit
        }

    def download_info(self, url):
        commit_info = self.commit_info(url)
        if commit_info == False:
            return False

        commit_date = commit_info['timestamp'][0:19].replace('T', ' ')

        return {
            'version': re.sub('[\-: ]', '.', commit_date),
            # We specifically use nodeload.github.com here because the download
            # URLs all redirect there, and some of the downloaders don't follow
            # HTTP redirect headers
            'url': 'https://nodeload.github.com/%s/zip/%s' % (commit_info['user_repo'], quote(commit_info['commit'])),
            'date': commit_date
        }

    def make_api_url(self, user_repo, suffix=''):
        return 'https://api.github.com/repos/%s%s' % (user_repo, suffix)
