import re

from ..pep440 import PEP440InvalidVersionError
from ..pep440 import PEP440Version
from ..pep440 import PEP440VersionSpecifier

from .json_api_client import JSONApiClient


class PyPiClient(JSONApiClient):
    @staticmethod
    def name_and_version(url):
        match = re.match(
            r"^https?://pypi\.org/project/([^/#?]+)(?:/([^/#?]+?)|/?)$", url
        )
        if match:
            return match.groups()

        return (None, None)

    def repo_info(self, url):
        name, _ = self.name_and_version(url)
        if not name:
            return None

        pypi_url = "https://pypi.org/pypi/{}/json".format(name)
        info = self.fetch_json(pypi_url)

        return {
            "name": name,
            "description": info["summary"],
            "homepage": info["home_page"]
            or info.get("project_urls", {}).get("Homepage"),
            "author": info["author"],
            "issues": info["bugtrack_url"]
            or info.get("project_urls", {}).get("Issues"),
        }

    def download_info(self, url, tag_prefix=None):
        """Branch or tag based releases are not supported."""
        return None

    def download_info_from_branch(self, url, default_branch=None):
        """Branch or tag based releases are not supported."""
        return None

    def download_info_from_tags(self, url, tag_prefix=None):
        """Branch or tag based releases are not supported."""
        return None

    def download_info_from_releases(self, url, asset_templates, tag_prefix=None):
        """
        Retrieve information about package

        :param url:
            The URL of the repository, in one of the forms:
              https://pypi.org/projects/{library_name}
              https://pypi.org/projects/{library_name}/{version}
            Grabs the info from the newest compatible release(s).

        :param tag_prefix:
            unused, present for API compatibility.

        :param asset_templates:
            A list of tuples of asset template and download_info.

            ```py
            [
                (
                    "coverage-${version}-cp33-*-win_amd64*.whl",
                    {
                        "platforms": ["windows-x64"],
                        "python_versions": ["3.3"]
                    }
                )
            ]
            ```

            Supported globs:

              * : any number of characters
              ? : single character placeholder

            Supported variables are:

              ${platform}
                A platform-arch string as given in "platforms" list.
                A separate explicit release is evaluated for each platform.
                If "platforms": ["*"] is specified, variable is set to "any".

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
                    "url": "https://files.pythonhosted.org/packages/.../coverage-4.2-cp33-cp33m-win_amd64.whl",
                    "version": "4.2",
                    "date": "2016-07-26 21:09:17",
                    "sha256": "bd4eba631f07cae8cdb9c55c144f165649e6701b962f9d604b4e00cf8802406c",
                    "platforms": ["windows-x64"],
                    "python_versions": ["3.3"]
                },
                ...
            ]
            ```
        """

        name, version = self.name_and_version(url)
        if not name:
            return None

        if version:
            return self._download_info_from_fixed_version(
                name, version, asset_templates
            )

        return self._download_info_from_latest_version(name, asset_templates)

    def _download_info_from_fixed_version(self, name, version, asset_templates):
        """
        Build download information from fixed version.

        :param name:
            The package name
        :param version:
            The package version
        :param asset_templates:
            A list of tuples of asset template and download_info.

        :return:
            ``None`` if no match, ``False`` if no commit, or a list of dicts with the
            following keys:
        """

        pypi_url = "https://pypi.org/pypi/{}/{}/json".format(name, version)
        assets = self.fetch_json(pypi_url)["urls"]

        asset_templates = self._expand_asset_variables(asset_templates)

        output = []
        for pattern, selectors in asset_templates:
            info = self._make_download_info(pattern, selectors, version, assets)
            if info:
                output.append(info)

        return output

    def _download_info_from_latest_version(self, name, asset_templates):
        """
        Build download information from latest compatible versions of each asset template.

        :param name:
            The package name
        :param version:
            The package version
        :param asset_templates:
            A list of tuples of asset template and download_info.

        :return:
            ``None`` if no match, ``False`` if no commit, or a list of dicts with the
            following keys:
        """

        pypi_url = "https://pypi.org/pypi/{}/json".format(name)

        # fetch dictionary of form `version: [asset, asset]`
        releases = self.fetch_json(pypi_url)["releases"]

        # create a list of valid pep440 versions
        versions = []
        for version in releases:
            try:
                versions.append(PEP440Version(version))
            except PEP440InvalidVersionError:
                continue

        asset_templates = self._expand_asset_variables(asset_templates)

        max_releases = self.settings.get("max_releases", 0)
        num_releases = [0] * len(asset_templates)

        # get latest compatible release for each asset template
        output = []
        for version in sorted(versions, reverse=True):
            # we don"t want beta releases!
            if not version.is_final:
                continue

            version_string = str(version)
            assets = releases[version_string]
            for idx, (pattern, selectors) in enumerate(asset_templates):
                if max_releases > 0 and num_releases[idx] >= max_releases:
                    continue
                info = self._make_download_info(pattern, selectors, version_string, assets)
                if not info:
                    continue
                output.append(info)
                num_releases[idx] += 1

            if max_releases > 0 and min(num_releases) >= max_releases:
                break

        return output

    @staticmethod
    def _make_download_info(pattern, selectors, version, assets):
        """
        Build download information for given asset template.

        :param pattern:
            The glob pattern of a given asset template
        :param selectors:
            The dictionary of release specification of given asset template from repository.json
        :param version:
            The package version
        :param assets:
            A list of dictionaries of asset information downloaded from PyPI.

        :return:
            ``None`` if no match, ``False`` if no commit, or a list of dicts with the
            following keys:
        """

        pattern = pattern.replace("${version}", version)
        pattern = pattern.replace(".", r"\.")
        pattern = pattern.replace("?", r".")
        pattern = pattern.replace("*", r".*?")
        regex = re.compile(pattern)

        python_versions = (PEP440Version(ver) for ver in selectors["python_versions"])

        for asset in assets:
            if asset["packagetype"] != "bdist_wheel":
                continue
            if asset["yanked"]:
                continue
            if not regex.match(asset["filename"]):
                continue

            specs = asset["requires_python"]
            if specs:
                specs = (
                    PEP440VersionSpecifier(spec)
                    for spec in asset["requires_python"].split(",")
                )
                if not all(ver in spec for spec in specs for ver in python_versions):
                    continue

            info = {
                "url": asset["url"],
                "version": version,
                "date": asset["upload_time"][0:19].replace("T", " "),
                "sha256": asset["digests"]["sha256"],
            }
            info.update(selectors)
            return info

        return None

    @staticmethod
    def _expand_asset_variables(asset_templates):
        output = []
        for pattern, spec in JSONApiClient._expand_asset_variables(asset_templates):
            if len(spec["python_versions"]) == 1:
                output.append((pattern, spec))
                continue

            for py_ver in spec["python_versions"]:
                new_spec = spec.copy()
                new_spec["python_versions"] = [py_ver]
                output.append((pattern, new_spec))

        return output
