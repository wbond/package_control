import re

from ..versions import version_sort, version_filter
from .json_api_client import JSONApiClient


_readme_filenames = [
    'readme',
    'readme.txt',
    'readme.md',
    'readme.mkd',
    'readme.mdown',
    'readme.markdown',
    'readme.textile',
    'readme.creole',
    'readme.rst'
]


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

        output = {
            'name': info['name'],
            'description': info['description'] or 'No description provided',
            'homepage': info['website'] or url,
            'author': info['owner'],
            'donate': u'https://www.gittip.com/%s/' % info['owner'],
            'readme': None
        }

        main_branch = self.branch_info(user_repo)
        if not main_branch:
            return output

        listing_url = self.make_api_url(user_repo, '/src/%s/' % main_branch)
        root_dir_info = self.fetch_json(listing_url)
        if not root_dir_info:
            return output

        for entry in root_dir_info['files']:
            if entry['path'].lower() in _readme_filenames:
                output['readme'] = 'https://bitbucket.org/%s/raw/%s/%s' % (user_repo,
                    main_branch, entry['path'])
                break

        return output

    def branch_info(self, user_repo):
        """
        Return the name of the default branch
        """

        main_branch_url = self.make_api_url(user_repo, '/main-branch')
        main_branch_info = self.fetch_json(main_branch_url)
        if main_branch_info == False:
            return False
        return main_branch_info['name']

    def commit_info(self, url):
        repo_match = re.match('https?://bitbucket.org/([^/]+/[^/]+)/?$', url)
        branch_match = re.match('https?://bitbucket.org/([^/]+/[^/]+)/src/([^/]+)/?$', url)
        tags_match = re.match('https?://bitbucket.org/([^/]+/[^#/]+)/?#tags$', url)

        if repo_match:
            # Since HG allows for arbitrary main branch names, we have to hit
            # this URL just to get that info
            user_repo = repo_match.group(1)
            commit = self.branch_info(user_repo)

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

        changeset_url = self.make_api_url(user_repo, '/changesets/%s' % commit)
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
            'url': 'https://bitbucket.org/%s/get/%s.zip' % (commit_info['user_repo'], commit_info['commit']),
            'date': commit_date
        }

    def make_api_url(self, user_repo, suffix=''):
        return 'https://api.bitbucket.org/1.0/repositories/%s%s' % (user_repo, suffix)
