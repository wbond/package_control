import json
from urllib.parse import urlencode, urlparse

from .client_exception import ClientException
from ..download_manager import http_get


class JSONApiClient:

    def __init__(self, settings):
        self.settings = settings

    def fetch(self, url):
        """
        Retrieves the contents of a URL

        :param url:
            The URL to download the content from

        :raises:
            DownloaderException: when there is an error downloading

        :return:
            The bytes/string
        """

        # If there are extra params for the domain name, add them
        extra_params = self.settings.get('query_string_params')
        domain_name = urlparse(url).netloc
        if extra_params and domain_name in extra_params:
            params = urlencode(extra_params[domain_name])
            joiner = '?%s' if url.find('?') == -1 else '&%s'
            url += joiner % params

        return http_get(url, self.settings, 'Error downloading repository.')

    def fetch_json(self, url):
        """
        Retrieves and parses the JSON from a URL

        :param url:
            The URL to download the JSON from

        :raises:
            ClientException: when there is an error parsing the response

        :return:
            A dict or list from the JSON
        """

        repository_json = self.fetch(url)

        try:
            return json.loads(repository_json.decode('utf-8'))
        except (ValueError):
            error_string = 'Error parsing JSON from URL %s.' % url
            raise ClientException(error_string)

    @staticmethod
    def _expand_asset_variables(asset_templates):
        """
        Expands the asset variables.

        Note: ``${version}`` is not replaced.

        :param asset_templates:
            A list of tuples of asset template and download_info.

            ```py
            [
                (
                    "Name-${version}-py${py_version}-*-x??.whl",
                    {
                        "platforms": ["windows-x64"],
                        "python_versions": ["3.3", "3.8"],
                        "sublime_text": ">=4107"
                    }
                )
            ]
            ```

            Supported variables are:

              ``${platform}``
                A platform-arch string as given in "platforms" list.
                A separate explicit release is evaluated for each platform.
                If "platforms": ['*'] is specified, variable is set to "any".

              ``${py_version}``
                Major and minor part of required python version without period.
                One of "33", "38" or any other valid python version supported by ST.

              ``${st_build}``
                Value of "st_specifier" stripped by leading operator
                "*"            => "any"
                ">=4107"       => "4107"
                "<4107"        => "4107"
                "4107 - 4126"  => "4107"

        :returns:
            A list of asset templates with all variables (except ``${version}``) resolved.

            ```py
            [
                (
                    "Name-${version}-py33-*-x??.whl",
                    {
                        "platforms": ["windows-x64"],
                        "python_versions": ["3.3"],
                        "sublime_text": ">=4107"
                    }
                ),
                (
                    "Name-${version}-py33-*-x??.whl",
                    {
                        "platforms": ["windows-x64"],
                        "python_versions": ["3.8"],
                        "sublime_text": ">=4107"
                    }
                )
            ]
            ```
        """

        output = []
        var = '${st_build}'
        for pattern, selectors in asset_templates:
            # resolve ${st_build}
            if var in pattern:
                # convert st_specifier version specifier to build number
                st_specifier = selectors['sublime_text']
                if st_specifier == '*':
                    st_build = 'any'
                elif st_specifier[0].isdigit():
                    # 4107, 4107 - 4126
                    st_build = st_specifier[:4]
                elif st_specifier[1].isdigit():
                    # <4107, >4107
                    st_build = st_specifier[1:]
                else:
                    # ==4107, <=4107, >=4107
                    st_build = st_specifier[2:]

                pattern = pattern.replace(var, st_build)

            output.append((pattern, selectors))

        def resolve(templates, var, key):
            for pattern, selectors in templates:
                if var not in pattern:
                    yield (pattern, selectors)
                    continue

                for value in selectors[key]:
                    new_selectors = selectors.copy()
                    new_selectors[key] = [value]
                    # remove `.` from python versions; n.r. for platforms
                    yield (pattern.replace(var, value.replace('.', '')), new_selectors)

            return None

        output = resolve(output, '${platform}', 'platforms')
        output = resolve(output, '${py_version}', 'python_versions')
        return list(output)
