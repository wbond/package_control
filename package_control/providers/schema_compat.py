from ..download_manager import update_url
from ..semver import SemVer


def platforms_to_releases(info, debug):
    """
    Accepts a dict from a schema version 1.0, 1.1 or 1.2 package containing
    a "platforms" key and converts it to a list of releases compatible with'
    schema version 2.0.

    :param info:
        The dict of package info

    :param debug:
        If debug information should be shown

    :return:
        A list of release dicts
    """

    output = []

    temp_releases = {}
    platforms = info.get('platforms')

    for platform in platforms:
        for release in platforms[platform]:
            key = '%s-%s' % (release['version'], release['url'])
            if key not in temp_releases:
                temp_releases[key] = {
                    'sublime_text': '<3000',
                    'version': release['version'],
                    'date': info.get('last_modified', '2011-08-01 00:00:00'),
                    'url': update_url(release['url'], debug),
                    'platforms': []
                }
            if platform == '*':
                temp_releases[key]['platforms'] = ['*']
            elif temp_releases[key]['platforms'] != ['*']:
                temp_releases[key]['platforms'].append(platform)

    for key in temp_releases:
        release = temp_releases[key]
        if release['platforms'] == ['windows', 'linux', 'osx']:
            release['platforms'] = ['*']
        output.append(release)

    return output


class SchemaVersion(SemVer):
    supported_versions = ('1.0', '1.1', '1.2', '2.0', '3.0.0')

    @classmethod
    def _parse(cls, ver):
        """
        Custom version string parsing to maintain backward compatibility.

        SemVer needs all of major, minor and patch parts being present in `ver`.

        :param ver:
            An integer, float or string containing a version string.

        :returns:
            List of (major, minor, patch)
        """
        try:
            if isinstance(ver, int):
                ver = float(ver)
            if isinstance(ver, float):
                ver = str(ver)
        except ValueError:
            raise ValueError('the "schema_version" is not a valid number.')

        if ver not in cls.supported_versions:
            raise ValueError(
                'the "schema_version" is not recognized. Must be one of: %s or %s.'
                % (', '.join(cls.supported_versions[:-1]), cls.supported_versions[-1])
            )

        if ver.count('.') == 1:
            ver += '.0'

        return SemVer._parse(ver)
