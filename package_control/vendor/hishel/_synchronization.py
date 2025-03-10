import types
import typing as tp
from threading import Lock as T_LOCK

from .. import anyio


class AsyncLock:
    def __init__(self) -> None:
        self._lock = anyio.Lock()

    async def __aenter__(self) -> None:
        await self._lock.acquire()

    async def __aexit__(
        self,
        exc_type: tp.Optional[tp.Type[BaseException]] = None,
        exc_value: tp.Optional[BaseException] = None,
        traceback: tp.Optional[types.TracebackType] = None,
    ) -> None:
        self._lock.release()


class Lock:
    def __init__(self) -> None:
        self._lock = T_LOCK()

    def __enter__(self) -> None:
        self._lock.acquire()

    def __exit__(
        self,
        exc_type: tp.Optional[tp.Type[BaseException]] = None,
        exc_value: tp.Optional[BaseException] = None,
        traceback: tp.Optional[types.TracebackType] = None,
    ) -> None:
        self._lock.release()
