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
from .upload import MAX_CHUNK_SIZE, MIN_CHUNK_SIZE, ONE_GB, UploadMixin

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
        *,
        auto_max_workers: bool = False,
        safe_mode: bool = False,
        target_seconds: float = 3.0,
        min_chunk_size: int = MIN_CHUNK_SIZE,
        max_chunk_size: int = MAX_CHUNK_SIZE,
        direct_upload_factor: float = 15.0,
        safe_max_workers: int = 2,
        safe_max_chunk_size: int = 8 * 1024 * 1024,
        safe_direct_upload_threshold: int = 2 * 1024 * 1024,
        max_ram_bytes: int = ONE_GB,
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
        self.auto_max_workers = auto_max_workers
        self.safe_mode = safe_mode
        self.target_seconds = float(target_seconds)
        self.min_chunk_size = int(min_chunk_size)
        self.max_chunk_size = int(max_chunk_size)
        self.direct_upload_factor = float(direct_upload_factor)
        self.safe_max_workers = max(1, int(safe_max_workers))
        self.safe_max_chunk_size = int(safe_max_chunk_size)
        self.safe_direct_upload_threshold = int(safe_direct_upload_threshold)
        self.max_ram_bytes = int(max_ram_bytes)
        self.dynamic_chunk_size: Optional[int] = None
        self.dynamic_chunk_threshold: Optional[int] = None
        self.measured_speed_bps: Optional[float] = None
        self.cancel_check: Optional[Callable[[], bool]] = None
        self._validate_upload_config()
        logger.debug("KDriveClient %s initialized for drive %s", __version__, self.drive_id)

    def _validate_upload_config(self) -> None:
        if self.parallelism < 1:
            raise ValueError("parallelism must be >= 1")
        if self.safe_max_workers < 1:
            raise ValueError("safe_max_workers must be >= 1")
        if self.target_seconds <= 0:
            raise ValueError("target_seconds must be > 0")
        if self.min_chunk_size <= 0:
            raise ValueError("min_chunk_size must be > 0")
        if self.max_chunk_size < self.min_chunk_size:
            raise ValueError("max_chunk_size must be >= min_chunk_size")
        if self.direct_upload_factor <= 0:
            raise ValueError("direct_upload_factor must be > 0")
        if self.safe_max_chunk_size < self.min_chunk_size:
            raise ValueError("safe_max_chunk_size must be >= min_chunk_size")
        if self.safe_direct_upload_threshold <= 0:
            raise ValueError("safe_direct_upload_threshold must be > 0")
        if self.max_ram_bytes <= 0:
            raise ValueError("max_ram_bytes must be > 0")

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
