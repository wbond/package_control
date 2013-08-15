import time


# A cache of channel and repository info to allow users to install multiple
# packages without having to wait for the metadata to be downloaded more
# than once. The keys are managed locally by the utilizing code.
_channel_repository_cache = {}


def clear_cache():
    global _channel_repository_cache
    _channel_repository_cache = {}


def get_cache(key, default=None):
    """
    Gets an in-memory cache value

    :param key:
        The string key

    :param default:
        The value to return if the key has not been set, or the ttl expired

    :return:
        The cached value, or default
    """

    struct = _channel_repository_cache.get(key, {})
    expires = struct.get('expires')
    if expires and expires > time.time():
        return struct.get('data')
    return default


def merge_cache_over_settings(destination, setting, key_prefix):
    """
    Take the cached value of `key` and put it into the key `setting` of
    the destination.settings dict. Merge the values by overlaying the
    cached setting over the existing info.

    :param destination:
        An object that has a `.settings` attribute that is a dict

    :param setting:
        The dict key to use when pushing the value into the settings dict

    :param key_prefix:
        The string to prefix to `setting` to make the cache key
    """

    existing = destination.settings.get(setting, {})
    value = get_cache(key_prefix + '.' + setting, {})
    if value:
        existing.update(value)
        destination.settings[setting] = existing


def merge_cache_under_settings(destination, setting, key_prefix, list_=False):
    """
    Take the cached value of `key` and put it into the key `setting` of
    the destination.settings dict. Merge the values by overlaying the
    existing setting value over the cached info.

    :param destination:
        An object that has a `.settings` attribute that is a dict

    :param setting:
        The dict key to use when pushing the value into the settings dict

    :param key_prefix:
        The string to prefix to `setting` to make the cache key

    :param list_:
        If a list should be used instead of a dict
    """

    default = {} if not list_ else []
    existing = destination.settings.get(setting)
    value = get_cache(key_prefix + '.' + setting, default)
    if value:
        if existing:
            if list_:
                # Prevent duplicate values
                base = dict(zip(value, [None]*len(value)))
                for val in existing:
                    if val in base:
                        continue
                    value.append(val)
            else:
                value.update(existing)
        destination.settings[setting] = value


def set_cache(key, data, ttl=300):
    """
    Sets an in-memory cache value

    :param key:
        The string key

    :param data:
        The data to cache

    :param ttl:
        The integer number of second to cache the data for
    """

    _channel_repository_cache[key] = {
        'data': data,
        'expires': time.time() + ttl
    }


def set_cache_over_settings(destination, setting, key_prefix, value, ttl):
    """
    Take the value passed, and merge it over the current `setting`. Once
    complete, take the value and set the cache `key` and destination.settings
    `setting` to that value, using the `ttl` for set_cache().

    :param destination:
        An object that has a `.settings` attribute that is a dict

    :param setting:
        The dict key to use when pushing the value into the settings dict

    :param key_prefix:
        The string to prefix to `setting` to make the cache key

    :param value:
        The value to set

    :param ttl:
        The cache ttl to use
    """

    existing = destination.settings.get(setting, {})
    existing.update(value)
    set_cache(key_prefix + '.' + setting, value, ttl)
    destination.settings[setting] = value


def set_cache_under_settings(destination, setting, key_prefix, value, ttl, list_=False):
    """
    Take the value passed, and merge the current `setting` over it. Once
    complete, take the value and set the cache `key` and destination.settings
    `setting` to that value, using the `ttl` for set_cache().

    :param destination:
        An object that has a `.settings` attribute that is a dict

    :param setting:
        The dict key to use when pushing the value into the settings dict

    :param key_prefix:
        The string to prefix to `setting` to make the cache key

    :param value:
        The value to set

    :param ttl:
        The cache ttl to use
    """

    default = {} if not list_ else []
    existing = destination.settings.get(setting, default)
    if value:
        if list_:
            value.extend(existing)
        else:
            value.update(existing)
        set_cache(key_prefix + '.' + setting, value, ttl)
        destination.settings[setting] = value
