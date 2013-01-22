import time


# A cache of channel and repository info to allow users to install multiple
# packages without having to wait for the metadata to be downloaded more
# than once. The keys are managed locally by the utilizing code.
_channel_repository_cache = {}


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
