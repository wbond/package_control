import base64
import json
import pickle
import typing as tp
from datetime import datetime

from ..httpcore import Request, Response

from ..hishel._utils import normalized_url

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

HEADERS_ENCODING = "iso-8859-1"
KNOWN_RESPONSE_EXTENSIONS = ("http_version", "reason_phrase")
KNOWN_REQUEST_EXTENSIONS = ("timeout", "sni_hostname")

__all__ = ("PickleSerializer", "JSONSerializer", "YAMLSerializer", "BaseSerializer", "clone_model")

T = tp.TypeVar("T", Request, Response)


def clone_model(model: T) -> T:
    if isinstance(model, Response):
        return Response(
            status=model.status,
            headers=model.headers,
            content=model.content,
            extensions={key: value for key, value in model.extensions.items() if key in KNOWN_RESPONSE_EXTENSIONS},
        )  # type: ignore
    else:
        return Request(
            method=model.method,
            url=normalized_url(model.url),
            headers=model.headers,
            extensions={key: value for key, value in model.extensions.items() if key in KNOWN_REQUEST_EXTENSIONS},
        )  # type: ignore


class Metadata(tp.TypedDict):
    number_of_uses: int
    created_at: datetime
    cache_key: str


class BaseSerializer:
    def dumps(self, response: Response, request: Request, metadata: Metadata) -> tp.Union[str, bytes]:
        raise NotImplementedError()

    def loads(self, data: tp.Union[str, bytes]) -> tp.Tuple[Response, Request, Metadata]:
        raise NotImplementedError()

    @property
    def is_binary(self) -> bool:
        raise NotImplementedError()


class PickleSerializer(BaseSerializer):
    """
    A simple pickle-based serializer.
    """

    def dumps(self, response: Response, request: Request, metadata: Metadata) -> tp.Union[str, bytes]:
        """
        Dumps the HTTP response and its HTTP request.

        :param response: An HTTP response
        :type response: Response
        :param request: An HTTP request
        :type request: Request
        :param metadata: Additional information about the stored response
        :type metadata: Metadata
        :return: Serialized response
        :rtype: tp.Union[str, bytes]
        """
        clone_response = clone_model(response)
        clone_request = clone_model(request)
        return pickle.dumps((clone_response, clone_request, metadata))

    def loads(self, data: tp.Union[str, bytes]) -> tp.Tuple[Response, Request, Metadata]:
        """
        Loads the HTTP response and its HTTP request from serialized data.

        :param data: Serialized data
        :type data: tp.Union[str, bytes]
        :return: HTTP response and its HTTP request
        :rtype: tp.Tuple[Response, Request, Metadata]
        """
        assert isinstance(data, bytes)
        return tp.cast(tp.Tuple[Response, Request, Metadata], pickle.loads(data))

    @property
    def is_binary(self) -> bool:  # pragma: no cover
        return True


class JSONSerializer(BaseSerializer):
    """A simple json-based serializer."""

    def dumps(self, response: Response, request: Request, metadata: Metadata) -> tp.Union[str, bytes]:
        """
        Dumps the HTTP response and its HTTP request.

        :param response: An HTTP response
        :type response: Response
        :param request: An HTTP request
        :type request: Request
        :param metadata: Additional information about the stored response
        :type metadata: Metadata
        :return: Serialized response
        :rtype: tp.Union[str, bytes]
        """
        response_dict = {
            "status": response.status,
            "headers": [
                (key.decode(HEADERS_ENCODING), value.decode(HEADERS_ENCODING)) for key, value in response.headers
            ],
            "content": base64.b64encode(response.content).decode("ascii"),
            "extensions": {
                key: value.decode("ascii")
                for key, value in response.extensions.items()
                if key in KNOWN_RESPONSE_EXTENSIONS
            },
        }

        request_dict = {
            "method": request.method.decode("ascii"),
            "url": normalized_url(request.url),
            "headers": [
                (key.decode(HEADERS_ENCODING), value.decode(HEADERS_ENCODING)) for key, value in request.headers
            ],
            "extensions": {key: value for key, value in request.extensions.items() if key in KNOWN_REQUEST_EXTENSIONS},
        }

        metadata_dict = {
            "cache_key": metadata["cache_key"],
            "number_of_uses": metadata["number_of_uses"],
            "created_at": metadata["created_at"].strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }

        full_json = {
            "response": response_dict,
            "request": request_dict,
            "metadata": metadata_dict,
        }

        return json.dumps(full_json, indent=4)

    def loads(self, data: tp.Union[str, bytes]) -> tp.Tuple[Response, Request, Metadata]:
        """
        Loads the HTTP response and its HTTP request from serialized data.

        :param data: Serialized data
        :type data: tp.Union[str, bytes]
        :return: HTTP response and its HTTP request
        :rtype: tp.Tuple[Response, Request, Metadata]
        """

        full_json = json.loads(data)

        response_dict = full_json["response"]
        request_dict = full_json["request"]
        metadata_dict = full_json["metadata"]
        metadata_dict["created_at"] = datetime.strptime(
            metadata_dict["created_at"],
            "%a, %d %b %Y %H:%M:%S GMT",
        )

        response = Response(
            status=response_dict["status"],
            headers=[
                (key.encode(HEADERS_ENCODING), value.encode(HEADERS_ENCODING))
                for key, value in response_dict["headers"]
            ],
            content=base64.b64decode(response_dict["content"].encode("ascii")),
            extensions={
                key: value.encode("ascii")
                for key, value in response_dict["extensions"].items()
                if key in KNOWN_RESPONSE_EXTENSIONS
            },
        )

        request = Request(
            method=request_dict["method"],
            url=request_dict["url"],
            headers=[
                (key.encode(HEADERS_ENCODING), value.encode(HEADERS_ENCODING)) for key, value in request_dict["headers"]
            ],
            extensions={
                key: value for key, value in request_dict["extensions"].items() if key in KNOWN_REQUEST_EXTENSIONS
            },
        )

        metadata = Metadata(
            cache_key=metadata_dict["cache_key"],
            created_at=metadata_dict["created_at"],
            number_of_uses=metadata_dict["number_of_uses"],
        )

        return response, request, metadata

    @property
    def is_binary(self) -> bool:
        return False


class YAMLSerializer(BaseSerializer):
    """A simple yaml-based serializer."""

    def dumps(self, response: Response, request: Request, metadata: Metadata) -> tp.Union[str, bytes]:
        """
        Dumps the HTTP response and its HTTP request.

        :param response: An HTTP response
        :type response: Response
        :param request: An HTTP request
        :type request: Request
        :param metadata: Additional information about the stored response
        :type metadata: Metadata
        :return: Serialized response
        :rtype: tp.Union[str, bytes]
        """
        if yaml is None:  # pragma: no cover
            raise RuntimeError(
                f"The `{type(self).__name__}` was used, but the required packages were not found. "
                "Check that you have `Hishel` installed with the `yaml` extension as shown.\n"
                "```pip install hishel[yaml]```"
            )
        response_dict = {
            "status": response.status,
            "headers": [
                (key.decode(HEADERS_ENCODING), value.decode(HEADERS_ENCODING)) for key, value in response.headers
            ],
            "content": base64.b64encode(response.content).decode("ascii"),
            "extensions": {
                key: value.decode("ascii")
                for key, value in response.extensions.items()
                if key in KNOWN_RESPONSE_EXTENSIONS
            },
        }

        request_dict = {
            "method": request.method.decode("ascii"),
            "url": normalized_url(request.url),
            "headers": [
                (key.decode(HEADERS_ENCODING), value.decode(HEADERS_ENCODING)) for key, value in request.headers
            ],
            "extensions": {key: value for key, value in request.extensions.items() if key in KNOWN_REQUEST_EXTENSIONS},
        }

        metadata_dict = {
            "cache_key": metadata["cache_key"],
            "number_of_uses": metadata["number_of_uses"],
            "created_at": metadata["created_at"].strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }

        full_json = {
            "response": response_dict,
            "request": request_dict,
            "metadata": metadata_dict,
        }

        return yaml.safe_dump(full_json, sort_keys=False)

    def loads(self, data: tp.Union[str, bytes]) -> tp.Tuple[Response, Request, Metadata]:
        """
        Loads the HTTP response and its HTTP request from serialized data.

        :param data: Serialized data
        :type data: tp.Union[str, bytes]
        :raises RuntimeError: When used without the `yaml` extension installed
        :return: HTTP response and its HTTP request
        :rtype: tp.Tuple[Response, Request, Metadata]
        """
        if yaml is None:  # pragma: no cover
            raise RuntimeError(
                f"The `{type(self).__name__}` was used, but the required packages were not found. "
                "Check that you have `Hishel` installed with the `yaml` extension as shown.\n"
                "```pip install hishel[yaml]```"
            )

        full_json = yaml.safe_load(data)

        response_dict = full_json["response"]
        request_dict = full_json["request"]
        metadata_dict = full_json["metadata"]
        metadata_dict["created_at"] = datetime.strptime(
            metadata_dict["created_at"],
            "%a, %d %b %Y %H:%M:%S GMT",
        )

        response = Response(
            status=response_dict["status"],
            headers=[
                (key.encode(HEADERS_ENCODING), value.encode(HEADERS_ENCODING))
                for key, value in response_dict["headers"]
            ],
            content=base64.b64decode(response_dict["content"].encode("ascii")),
            extensions={
                key: value.encode("ascii")
                for key, value in response_dict["extensions"].items()
                if key in KNOWN_RESPONSE_EXTENSIONS
            },
        )

        request = Request(
            method=request_dict["method"],
            url=request_dict["url"],
            headers=[
                (key.encode(HEADERS_ENCODING), value.encode(HEADERS_ENCODING)) for key, value in request_dict["headers"]
            ],
            extensions={
                key: value for key, value in request_dict["extensions"].items() if key in KNOWN_REQUEST_EXTENSIONS
            },
        )

        metadata = Metadata(
            cache_key=metadata_dict["cache_key"],
            created_at=metadata_dict["created_at"],
            number_of_uses=metadata_dict["number_of_uses"],
        )

        return response, request, metadata

    @property
    def is_binary(self) -> bool:  # pragma: no cover
        return False
