from .. import httpx

from ._async import *
from ._controller import *
from ._exceptions import *
from ._headers import *
from ._serializers import *
from ._sync import *
from ._lfu_cache import *


def install_cache() -> None:  # pragma: no cover
    httpx.AsyncClient = AsyncCacheClient  # type: ignore
    httpx.Client = CacheClient  # type: ignore


__version__ = "0.0.33"
