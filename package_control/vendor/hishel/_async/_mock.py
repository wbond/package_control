import typing as tp
from types import TracebackType

from ... import httpcore
from ... import httpx
from ...httpcore._async.interfaces import AsyncRequestInterface

if tp.TYPE_CHECKING:  # pragma: no cover
    from ...typing_extensions import Self

__all__ = ("MockAsyncConnectionPool", "MockAsyncTransport")


class MockAsyncConnectionPool(AsyncRequestInterface):
    async def handle_async_request(self, request: httpcore.Request) -> httpcore.Response:
        assert isinstance(request.stream, tp.AsyncIterable)
        data = b"".join([chunk async for chunk in request.stream])  # noqa: F841
        return self.mocked_responses.pop(0)

    def add_responses(self, responses: tp.List[httpcore.Response]) -> None:
        if not hasattr(self, "mocked_responses"):
            self.mocked_responses = []
        self.mocked_responses.extend(responses)

    async def __aenter__(self) -> "Self":
        return self

    async def __aexit__(
        self,
        exc_type: tp.Optional[tp.Type[BaseException]] = None,
        exc_value: tp.Optional[BaseException] = None,
        traceback: tp.Optional[TracebackType] = None,
    ) -> None: ...


class MockAsyncTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return self.mocked_responses.pop(0)

    def add_responses(self, responses: tp.List[httpx.Response]) -> None:
        if not hasattr(self, "mocked_responses"):
            self.mocked_responses = []
        self.mocked_responses.extend(responses)
