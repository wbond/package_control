import sqlite3
import typing as tp
from functools import partial
from pathlib import Path

from ..anyio import CapacityLimiter, to_thread


class Connection:
    def __init__(self, _real_connection: sqlite3.Connection) -> None:
        self._real_connection = _real_connection
        self._limiter = CapacityLimiter(1)

    async def __aenter__(self) -> "Connection":
        return self

    async def __aexit__(self, *args: tp.Any, **kwargs: tp.Any) -> None:
        return await self.close()

    async def close(self) -> None:
        return await to_thread.run_sync(
            self._real_connection.close, limiter=self._limiter
        )

    async def commit(self) -> None:
        return await to_thread.run_sync(
            self._real_connection.commit, limiter=self._limiter
        )

    async def rollback(self) -> None:
        return await to_thread.run_sync(
            self._real_connection.rollback, limiter=self._limiter
        )

    async def cursor(self) -> "Cursor":
        real_cursor = await to_thread.run_sync(
            self._real_connection.cursor, limiter=self._limiter
        )
        return Cursor(real_cursor, self._limiter)

    async def execute(self, sql: str, parameters: tp.Iterable[tp.Any] = ()) -> "Cursor":
        real_cursor = await to_thread.run_sync(
            self._real_connection.execute, sql, parameters, limiter=self._limiter
        )
        return Cursor(real_cursor, self._limiter)

    async def executemany(
        self, sql: str, seq_of_parameters: tp.Iterable[tp.Iterable[tp.Any]]
    ) -> "Cursor":
        real_cursor = await to_thread.run_sync(
            self._real_connection.executemany,
            sql,
            seq_of_parameters,
            limiter=self._limiter,
        )
        return Cursor(real_cursor, self._limiter)

    async def executescript(self, sql_script: str) -> "Cursor":
        real_cursor = await to_thread.run_sync(
            self._real_connection.executescript, sql_script, limiter=self._limiter
        )
        return Cursor(real_cursor, self._limiter)


class Cursor:
    def __init__(self, real_cursor: sqlite3.Cursor, limiter: CapacityLimiter) -> None:
        self._real_cursor = real_cursor
        self._limiter = limiter

    @property
    def description(
        self,
    ) -> tp.Union[
        tp.Tuple[tp.Tuple[str, None, None, None, None, None, None], ...], tp.Any
    ]:
        return self._real_cursor.description

    @property
    def rowcount(self) -> int:
        return self._real_cursor.rowcount

    @property
    def arraysize(self) -> int:
        return self._real_cursor.arraysize

    async def close(self) -> None:
        await to_thread.run_sync(self._real_cursor.close, limiter=self._limiter)

    async def execute(self, sql: str, parameters: tp.Iterable[tp.Any] = ()) -> "Cursor":
        real_cursor = await to_thread.run_sync(
            self._real_cursor.execute, sql, parameters, limiter=self._limiter
        )
        return Cursor(real_cursor, self._limiter)

    async def executemany(
        self, sql: str, seq_of_parameters: tp.Iterable[tp.Iterable[tp.Any]]
    ) -> "Cursor":
        real_cursor = await to_thread.run_sync(
            self._real_cursor.executemany, sql, seq_of_parameters, limiter=self._limiter
        )
        return Cursor(real_cursor, self._limiter)

    async def executescript(self, sql_script: str) -> "Cursor":
        real_cursor = await to_thread.run_sync(
            self._real_cursor.executescript, sql_script, limiter=self._limiter
        )
        return Cursor(real_cursor, self._limiter)

    async def fetchone(self) -> tp.Any:
        return await to_thread.run_sync(
            self._real_cursor.fetchone, limiter=self._limiter
        )

    async def fetchmany(self, size: tp.Union[int, None] = 1) -> tp.Any:
        return await to_thread.run_sync(
            self._real_cursor.fetchmany, size, limiter=self._limiter
        )

    async def fetchall(self) -> tp.Any:
        return await to_thread.run_sync(
            self._real_cursor.fetchall, limiter=self._limiter
        )


async def connect(
    database: tp.Union[str, bytes, Path], **kwargs: tp.Any
) -> "Connection":
    kwargs["check_same_thread"] = False
    real_connection = await to_thread.run_sync(
        partial(sqlite3.connect, database, **kwargs)
    )
    return Connection(real_connection)
