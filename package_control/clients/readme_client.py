import base64
import os
import re

from urllib.parse import urlencode

from .json_api_client import JSONApiClient


# Used to map file extensions to formats
_README_FORMATS = {
    '.md': 'markdown',
    '.mkd': 'markdown',
    '.mdown': 'markdown',
    '.markdown': 'markdown',
    '.textile': 'textile',
    '.creole': 'creole',
    '.rst': 'rst',
    '.txt': 'txt'
}


class ReadmeClient(JSONApiClient):

    def readme_info(self, url):
        """
        Retrieve the readme and info about it

        :param url:
            The URL of the readme file

        :raises:
            DownloaderException: if there is an error downloading the readme
            ClientException: if there is an error parsing the response

        :return:
            A dict with the following keys:
              `filename`
              `format` - `markdown`, `textile`, `creole`, `rst` or `txt`
              `contents` - contents of the readme as str/unicode
        """

        contents = None
        ext = None

        # Try to grab the contents of a GitHub-based readme by grabbing the cached
        # content of the readme API call
        github_match = re.match(
            r'https://raw\.github(?:usercontent)?\.com/([^/]+/[^/]+)/([^/]+)/'
            r'readme(\.(?:md|mkd|mdown|markdown|textile|creole|rst|txt))?$',
            url,
            re.I
        )
        if github_match:
            user_repo, branch, ext = github_match.groups()

            query_string = urlencode({'ref': branch})
            readme_json_url = 'https://api.github.com/repos/%s/readme?%s' % (user_repo, query_string)
            try:
                info = self.fetch_json(readme_json_url, prefer_cached=True)
                contents = base64.b64decode(info['content'])
            except ValueError:
                pass

        if not contents:
            contents = self.fetch(url)

        try:
            contents = contents.decode('utf-8')
        except UnicodeDecodeError:
            contents = contents.decode('cp1252', errors='replace')

        return {
            'filename': os.path.basename(url),
            'format': _README_FORMATS[ext.lower()] if ext else 'txt',
            'contents': contents
        }
