import time
import typing as tp

from ..anyio import to_thread
from botocore.exceptions import ClientError


def get_timestamp_in_ms() -> float:
    return time.time() * 1000


class S3Manager:
    def __init__(
        self, client: tp.Any, bucket_name: str, check_ttl_every: tp.Union[int, float], is_binary: bool = False
    ):
        self._client = client
        self._bucket_name = bucket_name
        self._is_binary = is_binary
        self._last_cleaned = time.monotonic()
        self._check_ttl_every = check_ttl_every

    def write_to(self, path: str, data: tp.Union[bytes, str], only_metadata: bool = False) -> None:
        path = "hishel-" + path
        if isinstance(data, str):
            data = data.encode("utf-8")

        created_at = None
        if only_metadata:
            try:
                response = self._client.get_object(
                    Bucket=self._bucket_name,
                    Key=path,
                )
                created_at = response["Metadata"]["created_at"]
            except Exception:
                pass

        self._client.put_object(
            Bucket=self._bucket_name,
            Key=path,
            Body=data,
            Metadata={"created_at": created_at or str(get_timestamp_in_ms())},
        )

    def read_from(self, path: str) -> tp.Union[bytes, str]:
        path = "hishel-" + path
        response = self._client.get_object(
            Bucket=self._bucket_name,
            Key=path,
        )

        content = response["Body"].read()

        if self._is_binary:  # pragma: no cover
            return tp.cast(bytes, content)

        return tp.cast(str, content.decode("utf-8"))

    def remove_expired(self, ttl: int, key: str) -> None:
        path = "hishel-" + key

        if time.monotonic() - self._last_cleaned < self._check_ttl_every:
            try:
                response = self._client.get_object(Bucket=self._bucket_name, Key=path)
                if get_timestamp_in_ms() - float(response["Metadata"]["created_at"]) > ttl:
                    self._client.delete_object(Bucket=self._bucket_name, Key=path)
                return
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    return
                raise e

        self._last_cleaned = time.monotonic()
        for obj in self._client.list_objects(Bucket=self._bucket_name).get("Contents", []):
            if not obj["Key"].startswith("hishel-"):  # pragma: no cover
                continue

            if get_timestamp_in_ms() - float(obj["Metadata"]["created_at"]) > ttl:
                self._client.delete_object(Bucket=self._bucket_name, Key=obj["Key"])

    def remove_entry(self, key: str) -> None:
        path = "hishel-" + key
        self._client.delete_object(Bucket=self._bucket_name, Key=path)


class AsyncS3Manager:  # pragma: no cover
    def __init__(
        self, client: tp.Any, bucket_name: str, check_ttl_every: tp.Union[int, float], is_binary: bool = False
    ):
        self._sync_manager = S3Manager(client, bucket_name, check_ttl_every, is_binary)

    async def write_to(self, path: str, data: tp.Union[bytes, str], only_metadata: bool = False) -> None:
        return await to_thread.run_sync(self._sync_manager.write_to, path, data, only_metadata)

    async def read_from(self, path: str) -> tp.Union[bytes, str]:
        return await to_thread.run_sync(self._sync_manager.read_from, path)

    async def remove_expired(self, ttl: int, key: str) -> None:
        return await to_thread.run_sync(self._sync_manager.remove_expired, ttl, key)

    async def remove_entry(self, key: str) -> None:
        return await to_thread.run_sync(self._sync_manager.remove_entry, key)
