from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional, Union

from .client import KDriveClient
from .http import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, REQUESTS_PER_MINUTE, TimeoutValue
from .models import DriveFile, KDriveFile
from .upload import UploadCancelled


class AsyncKDriveClient:
    """Async façade over :class:`KDriveClient` using ``asyncio.to_thread``.

    Long uploads honour :meth:`cancel` via ``cancel_check`` on the sync client.
    Optional dependency: install ``httpx`` only if you later swap the transport;
    the default path reuses the sync ``requests`` pipeline in a worker thread.
    """

    def __init__(
        self,
        token: str,
        drive_id: Union[str, int],
        *,
        base_url: str = "https://api.infomaniak.com",
        parallelism: int = 4,
        timeout: TimeoutValue = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        rate_limit: int = REQUESTS_PER_MINUTE,
        use_auto_chunk_size: bool = False,
    ):
        self._sync = KDriveClient(
            token,
            drive_id,
            base_url=base_url,
            parallelism=parallelism,
            timeout=timeout,
            max_retries=max_retries,
            rate_limit=rate_limit,
            use_auto_chunk_size=use_auto_chunk_size,
        )
        self._cancelled = False
        self._sync.cancel_check = lambda: self._cancelled

    @property
    def sync(self) -> KDriveClient:
        return self._sync

    def cancel(self) -> None:
        """Request cancellation of in-flight upload chunk loops."""
        self._cancelled = True

    def reset_cancel(self) -> None:
        self._cancelled = False

    async def __aenter__(self) -> "AsyncKDriveClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await asyncio.to_thread(self._sync.close)

    async def _run(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(fn, *args, **kwargs)

    async def upload(self, file: KDriveFile, **kwargs: Any) -> DriveFile:
        self.reset_cancel()
        try:
            return await self._run(self._sync.upload, file, **kwargs)
        except UploadCancelled:
            raise

    async def upload_batch(self, files, **kwargs: Any):
        self.reset_cancel()
        return await self._run(self._sync.upload_batch, files, **kwargs)

    async def download(self, file_id: Union[str, int], **kwargs: Any) -> bytes:
        return await self._run(self._sync.download, file_id, **kwargs)

    async def download_to_path(self, file_id: Union[str, int], destination, **kwargs: Any):
        return await self._run(self._sync.download_to_path, file_id, destination, **kwargs)

    async def get_file(self, file_id: Union[str, int], **kwargs: Any):
        return await self._run(self._sync.get_file, file_id, **kwargs)

    async def list_files(self, directory_id: Union[str, int] = 1, **kwargs: Any):
        return await self._run(self._sync.list_files, directory_id, **kwargs)

    async def create_directory(self, parent_id: Union[str, int], name: str, **kwargs: Any):
        return await self._run(self._sync.create_directory, parent_id, name, **kwargs)

    async def search(self, **kwargs: Any):
        return await self._run(self._sync.search, **kwargs)

    async def trash(self, file_id: Union[str, int]):
        return await self._run(self._sync.trash, file_id)

    async def bootstrap(self, **kwargs: Any):
        return await self._run(self._sync.bootstrap, **kwargs)

    async def get_drive(self, **kwargs: Any):
        return await self._run(self._sync.get_drive, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """Expose remaining sync methods as awaitable callables."""
        attr = getattr(self._sync, name)
        if not callable(attr):
            return attr

        async def _async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await asyncio.to_thread(attr, *args, **kwargs)

        return _async_wrapper
