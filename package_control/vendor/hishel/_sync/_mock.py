import typing as tp
from types import TracebackType

from ... import httpcore
from ... import httpx
from ...httpcore._sync.interfaces import RequestInterface

if tp.TYPE_CHECKING:  # pragma: no cover
    from ...typing_extensions import Self

__all__ = ("MockConnectionPool", "MockTransport")


class MockConnectionPool(RequestInterface):
    def handle_request(self, request: httpcore.Request) -> httpcore.Response:
        assert isinstance(request.stream, tp.Iterable)
        data = b"".join([chunk for chunk in request.stream])  # noqa: F841
        return self.mocked_responses.pop(0)

    def add_responses(self, responses: tp.List[httpcore.Response]) -> None:
        if not hasattr(self, "mocked_responses"):
            self.mocked_responses = []
        self.mocked_responses.extend(responses)

    def __enter__(self) -> "Self":
        return self

    def __exit__(
        self,
        exc_type: tp.Optional[tp.Type[BaseException]] = None,
        exc_value: tp.Optional[BaseException] = None,
        traceback: tp.Optional[TracebackType] = None,
    ) -> None: ...


class MockTransport(httpx.BaseTransport):
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self.mocked_responses.pop(0)

    def add_responses(self, responses: tp.List[httpx.Response]) -> None:
        if not hasattr(self, "mocked_responses"):
            self.mocked_responses = []
        self.mocked_responses.extend(responses)
