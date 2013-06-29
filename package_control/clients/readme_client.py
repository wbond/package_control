import re
import os
import base64

try:
    # Python 3
    from urllib.parse import urlencode
except (ImportError):
    # Python 2
    from urllib import urlencode

from .json_api_client import JSONApiClient


# Used to map file extensions to formats
_readme_formats = {
    '.md': 'markdown',
    '.mkd': 'markdown',
    '.mdown': 'markdown',
    '.markdown': 'markdown',
    '.textile': 'textile',
    '.creole': 'creole',
    '.rst': 'rst'
}


class ReadmeClient(JSONApiClient):

    def readme_info(self, url):
        """
        Retrieve the readme and info about it

        :param url:
            The URL of the readme file

        :return:
            False if error, or a dict with the following keys:
              `filename`
              `format` - `markdown`, `textile`, `creole`, `rst` or `txt`
              `contents` - contents of the readme as str/unicode
        """

        contents = None

        # Try to grab the contents of a GitHub-based readme by grabbing the cached
        # content of the readme API call
        github_match = re.match('https://raw.github.com/([^/]+/[^/]+)/([^/]+)/readme(\.(md|mkd|mdown|markdown|textile|creole|rst|txt))?$', url, re.I)
        if github_match:
            user_repo = github_match.group(1)
            branch = github_match.group(2)

            query_string = urlencode({'ref': branch})
            readme_json_url = 'https://api.github.com/repos/%s/readme?%s' % (user_repo, query_string)
            info = self.fetch_json(readme_json_url, prefer_cached=True)
            if info:
                try:
                    contents = base64.b64decode(info['content'])
                except (ValueError) as e:
                    pass

        if not contents:
            contents = self.fetch(url)
            if not contents:
                return False

        basename, ext = os.path.splitext(url)
        format = 'txt'
        ext = ext.lower()
        if ext in _readme_formats:
            format = _readme_formats[ext]

        try:
            contents = contents.decode('utf-8')
        except (UnicodeDecodeError) as e:
            contents = contents.decode('cp1252', errors='replace')

        return {
            'filename': os.path.basename(url),
            'format': format,
            'contents': contents
        }
