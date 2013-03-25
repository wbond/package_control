import re

from ..versions import version_sort, version_filter
from .json_api_client import JSONApiClient


class BitBucketClient(JSONApiClient):
    def repo_info(self, url):
        repo_match = re.match('https?://bitbucket.org/([^/]+/[^/]+)/?$', url)
        if repo_match == None:
            return False

        user_repo = repo_match.group(1)
        api_url = self.make_api_url(user_repo)

        info = self.fetch_json(api_url)
        if not info:
            return info

        return {
            'name': info['name'],
            'description': info['description'] or 'No description provided',
            'homepage': info['website'] or url,
            'author': info['owner'],
            'user_repo': user_repo
        }

    def commit_info(self, url):
        repo_match = re.match('https?://bitbucket.org/([^/]+/[^/]+)/?$', url)
        branch_match = re.match('https?://bitbucket.org/([^/]+/[^/]+)/src/([^/]+)/?$', url)
        tags_match = re.match('https?://bitbucket.org/([^/]+/[^#/]+)/?#tags$', url)
        
        if repo_match:
            # Since HG allows for arbitrary main branch names, we have to hit
            # this URL just to get that info
            user_repo = repo_match.group(1)
            main_branch_url = self.make_api_url(user_repo, '/main-branch')
            main_branch_info = self.fetch_json(main_branch_url)
            if main_branch_info == False:
                return False
            commit = main_branch_info['name']

        elif branch_match:
            user_repo = branch_match.group(1)
            commit = branch_match.group(2)
        
        elif tags_match:
            user_repo = tags_match.group(1)
            tags_url = self.make_api_url(user_repo, '/tags')
            tags_list = self.fetch_json(tags_url)
            if tags_list == False:
                return False
            tags = version_filter(tags_list.keys())
            tags = version_sort(tags, reverse=True)
            commit = tags[0]

        else:
            return False

        changeset_url = self.make_api_url(user_repo, '/changesets/' + commit)
        commit_info = self.fetch_json(changeset_url)
        if commit_info == False:
            return False

        return {
            'user_repo': user_repo,
            'timestamp': commit_info['timestamp'],
            'commit': commit_info['node']
        }

    def download_info(self, url):
        commit_info = self.commit_info(url)
        if commit_info == False:
            return False

        commit_date = commit_info['timestamp'][0:19]

        return {
            'version': re.sub('[\-: ]', '.', commit_date),
            'url': 'https://bitbucket.org/' + commit_info['user_repo'] + '/get/' + commit_info['commit'] + '.zip',
            'date': commit_date
        }

    def make_api_url(self, user_repo, suffix=''):
        return 'https://api.bitbucket.org/1.0/repositories/' + user_repo + suffix
