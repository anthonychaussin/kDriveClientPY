from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Sequence, Union

import requests

from ._version import __version__
from .models import (
    DriveDirectory,
    DriveEntry,
    DriveFile,
    KDriveApiException,
    PaginatedList,
    parse_drive_entry,
)

JsonDict = Dict[str, Any]
WithParam = Union[str, Sequence[str]]
TimeoutValue = Union[float, tuple]

REQUESTS_PER_MINUTE = 60
DEFAULT_TIMEOUT: TimeoutValue = (10.0, 120.0)
DEFAULT_MAX_RETRIES = 3
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

logger = logging.getLogger("kdrive_client")


class FixedWindowRateLimiter:
    """Fixed-window limiter matching Infomaniak's 60 requests/minute cap."""

    def __init__(self, limit: int = REQUESTS_PER_MINUTE, window_seconds: float = 60.0):
        self.limit = max(1, limit)
        self.window_seconds = window_seconds
        self._timestamps: Deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                cutoff = now - self.window_seconds
                while self._timestamps and self._timestamps[0] <= cutoff:
                    self._timestamps.popleft()
                if len(self._timestamps) < self.limit:
                    self._timestamps.append(now)
                    return
                wait = self.window_seconds - (now - self._timestamps[0])
            time.sleep(max(0.01, wait))


class HttpPipeline:
    """Shared HTTP session, rate limiting, retries, and response helpers."""

    def __init__(
        self,
        token: str,
        drive_id: Union[str, int],
        *,
        base_url: str = "https://api.infomaniak.com",
        timeout: TimeoutValue = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        rate_limit: int = REQUESTS_PER_MINUTE,
        session: Optional[requests.Session] = None,
    ):
        self.token = token
        self.drive_id = str(drive_id)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.rate_limiter = FixedWindowRateLimiter(limit=rate_limit)
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "User-Agent": f"kdrive_client/{__version__}",
            }
        )
        self._session_lock = threading.Lock()

    def close(self) -> None:
        self.session.close()

    def url(self, version: int, path: str) -> str:
        return f"{self.base_url}/{version}/drive/{self.drive_id}/{path.lstrip('/')}"

    def account_url(self, version: int, path: str) -> str:
        return f"{self.base_url}/{version}/{path.lstrip('/')}"

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Any = None,
        data: Any = None,
        headers: Optional[Dict[str, str]] = None,
        stream: bool = False,
        allow_redirects: bool = True,
        binary: bool = False,
    ) -> requests.Response:
        attempt = 0
        while True:
            self.rate_limiter.acquire()
            with self._session_lock:
                response = self.session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    data=data,
                    headers=headers,
                    timeout=self.timeout,
                    stream=stream,
                    allow_redirects=allow_redirects,
                )
            if response.status_code in RETRYABLE_STATUS and attempt < self.max_retries:
                delay = self._retry_delay(response, attempt)
                logger.info(
                    "Retryable status %s for %s %s; sleeping %.2fs",
                    response.status_code,
                    method,
                    url,
                    delay,
                )
                attempt += 1
                time.sleep(delay)
                continue
            return response

    @staticmethod
    def _retry_delay(response: requests.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        return min(30.0, (2**attempt) + 0.1 * attempt)

    def raise_api_error(self, response: requests.Response) -> None:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                raise KDriveApiException.from_payload(
                    payload,
                    status=response.status_code,
                    fallback_text=response.text,
                )
        except (ValueError, TypeError):
            pass
        raise KDriveApiException(
            str(response.status_code),
            response.text or response.reason,
            status=response.status_code,
        )

    def handle_json(self, response: requests.Response) -> JsonDict:
        try:
            payload = response.json()
        except ValueError:
            if response.ok:
                raise KDriveApiException(
                    "invalid_json",
                    "Expected JSON response",
                    status=response.status_code,
                )
            self.raise_api_error(response)
            raise  # pragma: no cover

        if not isinstance(payload, dict):
            raise KDriveApiException(
                "unexpected_payload",
                "Expected JSON object response",
                status=response.status_code,
            )

        if not response.ok or payload.get("result") == "error":
            raise KDriveApiException.from_payload(
                payload,
                status=response.status_code,
                fallback_text=response.text,
            )
        return payload

    def handle_binary(self, response: requests.Response) -> bytes:
        if response.ok:
            return response.content
        self.raise_api_error(response)
        return b""  # pragma: no cover

    @staticmethod
    def data(payload: JsonDict) -> Any:
        return payload.get("data")

    @staticmethod
    def enum_value(value: Any) -> Any:
        return value.value if hasattr(value, "value") else value

    def as_params(self, values: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not values:
            return {}
        params: Dict[str, Any] = {}
        for key, value in values.items():
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                params[key] = [self.enum_value(v) for v in value]
            else:
                params[key] = self.enum_value(value)
        return params

    @staticmethod
    def normalize_with(with_: Optional[WithParam]) -> Optional[List[str]]:
        if with_ is None:
            return None
        if isinstance(with_, str):
            return [with_]
        return list(with_)

    def paginated_entries(self, payload: JsonDict) -> PaginatedList[DriveEntry]:
        raw_items = self.data(payload) or []
        items = [parse_drive_entry(item) for item in raw_items]
        return PaginatedList(
            items=items,
            cursor=payload.get("cursor"),
            has_more=bool(payload.get("has_more", False)),
            response_at=payload.get("response_at"),
        )

    def parse_upload_result(self, data: Any) -> DriveFile:
        if isinstance(data, dict):
            if "file" in data and isinstance(data["file"], dict):
                entry = parse_drive_entry(data["file"])
            else:
                entry = parse_drive_entry(data)
            if isinstance(entry, DriveFile):
                return entry
            raise KDriveApiException(
                "unexpected_type",
                f"Expected file upload result, got type={entry.type}",
            )
        raise KDriveApiException("unexpected_payload", "Upload response missing file data")

    def parse_entry(self, data: Any, *, expected: Optional[str] = None) -> DriveEntry:
        if not isinstance(data, dict):
            raise KDriveApiException("unexpected_payload", "Missing entry payload")
        entry = parse_drive_entry(data)
        if expected == "dir" and not isinstance(entry, DriveDirectory):
            raise KDriveApiException("unexpected_type", f"Expected directory, got type={entry.type}")
        if expected == "file" and not isinstance(entry, DriveFile):
            raise KDriveApiException("unexpected_type", f"Expected file, got type={entry.type}")
        return entry

    def json_request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Any = None,
        data: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> JsonDict:
        response = self.request(
            method,
            url,
            params=params,
            json=json,
            data=data,
            headers=headers,
        )
        return self.handle_json(response)
