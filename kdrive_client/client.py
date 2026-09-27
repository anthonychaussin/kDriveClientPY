from __future__ import annotations

import logging
from typing import Callable, Optional, Union

from ._version import __version__
from .categories import CategoriesMixin
from .comments import CommentsMixin
from .download import DownloadMixin
from .drive import DriveMixin
from .favorites import FavoritesMixin
from .files import FilesMixin
from .http import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, REQUESTS_PER_MINUTE, HttpPipeline, TimeoutValue
from .shares import SharesMixin
from .smart import SmartMixin
from .trash import TrashMixin
from .upload import UploadMixin

logger = logging.getLogger("kdrive_client")


class KDriveClient(
    UploadMixin,
    DownloadMixin,
    FilesMixin,
    TrashMixin,
    FavoritesMixin,
    SharesMixin,
    CommentsMixin,
    CategoriesMixin,
    DriveMixin,
    SmartMixin,
    HttpPipeline,
):
    """Infomaniak kDrive API client — domain mixins composed over a shared HTTP pipeline."""

    def __init__(
        self,
        token: str,
        drive_id: Union[str, int],
        base_url: str = "https://api.infomaniak.com",
        parallelism: int = 4,
        timeout: TimeoutValue = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        rate_limit: int = REQUESTS_PER_MINUTE,
        use_auto_chunk_size: bool = False,
    ):
        HttpPipeline.__init__(
            self,
            token,
            drive_id,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            rate_limit=rate_limit,
        )
        self.parallelism = max(1, parallelism)
        self.progress_callback: Optional[Callable[[float], None]] = None
        self.download_progress_callback: Optional[Callable[[float], None]] = None
        self.use_auto_chunk_size = use_auto_chunk_size
        self.dynamic_chunk_size: Optional[int] = None
        self.dynamic_chunk_threshold: Optional[int] = None
        self.cancel_check: Optional[Callable[[], bool]] = None
        logger.debug("KDriveClient %s initialized for drive %s", __version__, self.drive_id)

    def __enter__(self) -> "KDriveClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # Backward-compatible aliases for private helpers used by older call sites / tests
    def _url(self, version: int, path: str) -> str:
        return self.url(version, path)

    def _request(self, *args, **kwargs):
        return self.request(*args, **kwargs)

    def _handle_json(self, response):
        return self.handle_json(response)

    def _handle_binary(self, response):
        return self.handle_binary(response)

    def _data(self, payload):
        return self.data(payload)

    def _as_params(self, values):
        return self.as_params(values)

    def _paginated_entries(self, payload):
        return self.paginated_entries(payload)

    def _parse_entry(self, data, *, expected=None):
        return self.parse_entry(data, expected=expected)

    def _parse_upload_result(self, data):
        return self.parse_upload_result(data)

    def _raise_api_error(self, response):
        return self.raise_api_error(response)

    @staticmethod
    def _enum_value(value):
        return HttpPipeline.enum_value(value)

    @staticmethod
    def _normalize_with(with_):
        return HttpPipeline.normalize_with(with_)
