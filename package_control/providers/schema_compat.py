from ..download_manager import update_url


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
            if not key in temp_releases:
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
