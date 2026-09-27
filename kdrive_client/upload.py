from __future__ import annotations

import hashlib
import io
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Literal, Optional, Sequence, Union

from .enums import ConflictMode
from .models import DriveFile, KDriveFile, UploadSession

JsonDict = Dict[str, Any]
HashAlgorithm = Literal["sha256", "xxh3"]

DEFAULT_CHUNK_THRESHOLD = 100 * 1024 * 1024  # 100 MiB (API recommendation)
DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MiB
MIN_CHUNK_SIZE = 1024 * 1024
MAX_CHUNK_SIZE = 100 * 1024 * 1024
PROBE_BYTES = 256 * 1024
ONE_MB = 1024 * 1024
ONE_GB = 1024 * ONE_MB


def _resolve_hasher(algorithm: HashAlgorithm):
    """Return (name, factory) for the chunk hash algorithm."""
    if algorithm == "xxh3":
        try:
            import xxhash  # type: ignore[import-untyped]

            return "xxh3", lambda: xxhash.xxh3_64()
        except ImportError:
            pass
    return "sha256", hashlib.sha256


def suggest_chunk_size(
    bytes_per_second: float,
    parallelism: int = 4,
    *,
    target_seconds: float = 2.0,
    min_chunk_size: int = MIN_CHUNK_SIZE,
    max_chunk_size: int = MAX_CHUNK_SIZE,
) -> int:
    """Pick a chunk size from a measured upload bandwidth (bytes/s)."""
    if bytes_per_second <= 0:
        return max(min_chunk_size, DEFAULT_CHUNK_SIZE)
    raw = int(bytes_per_second * target_seconds / max(1, parallelism))
    aligned = max(min_chunk_size, min(max_chunk_size, raw))
    # Round down to 256 KiB boundary
    return max(min_chunk_size, (aligned // (256 * 1024)) * (256 * 1024))


def suggest_direct_threshold(
    bytes_per_second: float,
    *,
    direct_upload_factor: float = 15.0,
    min_threshold: int = 10 * 1024 * 1024,
    max_threshold: int = DEFAULT_CHUNK_THRESHOLD,
) -> int:
    """Derive direct-vs-chunked threshold from bandwidth."""
    if bytes_per_second <= 0:
        return max_threshold
    raw = int(bytes_per_second * direct_upload_factor)
    return max(min_threshold, min(max_threshold, raw))


class UploadCancelled(Exception):
    """Raised when an upload is cancelled via cancel_check."""


class UploadMixin:
    """File upload (direct, chunked, batch session) endpoints."""

    parallelism: int
    progress_callback: Optional[Callable[[float], None]]
    use_auto_chunk_size: bool
    auto_max_workers: bool
    safe_mode: bool
    target_seconds: float
    min_chunk_size: int
    max_chunk_size: int
    direct_upload_factor: float
    safe_max_workers: int
    safe_max_chunk_size: int
    safe_direct_upload_threshold: int
    max_ram_bytes: int
    dynamic_chunk_size: Optional[int]
    dynamic_chunk_threshold: Optional[int]
    measured_speed_bps: Optional[float]
    cancel_check: Optional[Callable[[], bool]]

    def measure_upload_bandwidth(self, sample_size: int = PROBE_BYTES) -> float:
        """Rough upload bandwidth probe (bytes/s) via a tiny direct upload then trash."""
        probe = io.BytesIO(b"\0" * max(1024, sample_size))
        file = KDriveFile(
            name=f".kdrive_probe_{int(time.time())}.bin",
            directory_id=1,
            content=probe,
            total_size=max(1024, sample_size),
        )
        started = time.monotonic()
        uploaded = self.upload_direct(file, conflict=ConflictMode.RENAME)
        elapsed = max(0.001, time.monotonic() - started)
        try:
            self.trash(uploaded.id)
        except Exception:
            pass
        return file.total_size / elapsed

    def _ensure_auto_sizing(self) -> None:
        if self.dynamic_chunk_size is not None and self.dynamic_chunk_threshold is not None:
            return
        try:
            bps = self.measure_upload_bandwidth()
            self.measured_speed_bps = bps
            self.dynamic_chunk_size = suggest_chunk_size(
                bps,
                self.parallelism,
                target_seconds=self.target_seconds,
                min_chunk_size=self.min_chunk_size,
                max_chunk_size=self.max_chunk_size,
            )
            self.dynamic_chunk_threshold = suggest_direct_threshold(
                bps,
                direct_upload_factor=self.direct_upload_factor,
            )
            if self.safe_mode:
                self.dynamic_chunk_size = min(self.dynamic_chunk_size, self.safe_max_chunk_size)
                self.dynamic_chunk_threshold = min(
                    self.dynamic_chunk_threshold,
                    self.safe_direct_upload_threshold,
                )
        except Exception:
            self.dynamic_chunk_size = DEFAULT_CHUNK_SIZE
            self.dynamic_chunk_threshold = DEFAULT_CHUNK_THRESHOLD
            if self.safe_mode:
                self.dynamic_chunk_size = min(self.dynamic_chunk_size, self.safe_max_chunk_size)
                self.dynamic_chunk_threshold = min(
                    self.dynamic_chunk_threshold,
                    self.safe_direct_upload_threshold,
                )

    def resolve_chunk_size(
        self,
        chunk_size: Optional[int] = None,
        *,
        use_auto_chunk_size: Optional[bool] = None,
    ) -> int:
        if chunk_size is not None:
            size = max(self.min_chunk_size, chunk_size)
        else:
            auto = self.use_auto_chunk_size if use_auto_chunk_size is None else use_auto_chunk_size
            if auto:
                self._ensure_auto_sizing()
                size = self.dynamic_chunk_size or DEFAULT_CHUNK_SIZE
            else:
                size = DEFAULT_CHUNK_SIZE
        size = min(size, self.max_chunk_size)
        if self.safe_mode:
            size = min(size, self.safe_max_chunk_size)
        # Cap so at least one chunk buffer fits in RAM budget
        size = min(size, max(self.min_chunk_size, self.max_ram_bytes))
        return max(self.min_chunk_size, size)

    def resolve_chunk_threshold(
        self,
        chunk_threshold: Optional[int] = None,
        *,
        use_auto_chunk_size: Optional[bool] = None,
    ) -> int:
        if chunk_threshold is not None:
            threshold = chunk_threshold
        else:
            auto = self.use_auto_chunk_size if use_auto_chunk_size is None else use_auto_chunk_size
            if auto:
                self._ensure_auto_sizing()
                threshold = self.dynamic_chunk_threshold or DEFAULT_CHUNK_THRESHOLD
            else:
                threshold = DEFAULT_CHUNK_THRESHOLD
        if self.safe_mode:
            threshold = min(threshold, self.safe_direct_upload_threshold)
        return threshold

    def compute_upload_workers(self, *, chunk_size: int, total_chunks: int) -> int:
        """Resolve parallelism for a chunked upload (auto workers + safe + RAM)."""
        workers = max(1, self.parallelism)
        if self.auto_max_workers:
            workers = self._compute_auto_workers(total_chunks)
        if self.safe_mode:
            workers = min(workers, self.safe_max_workers)
        workers = min(workers, self._max_workers_by_ram(chunk_size))
        return max(1, workers)

    def _compute_auto_workers(self, total_chunks: int) -> int:
        max_workers = max(self.parallelism, 1)
        if total_chunks <= 1:
            return 1
        speed = self.measured_speed_bps
        if speed is not None:
            if speed < 2 * ONE_MB:
                return 1
            if speed < 5 * ONE_MB:
                return min(2, max_workers)
        if total_chunks < 4:
            return min(2, max_workers)
        if total_chunks < 8:
            return min(4, max_workers)
        return min(8, max_workers)

    def _max_workers_by_ram(self, chunk_size: int) -> int:
        if chunk_size <= 0:
            return 1
        return max(1, int(self.max_ram_bytes // chunk_size))

    def _raise_if_cancelled(self) -> None:
        check = getattr(self, "cancel_check", None)
        if check is not None and check():
            raise UploadCancelled("Upload cancelled")

    def upload(
        self,
        file: KDriveFile,
        *,
        chunk_size: Optional[int] = None,
        chunk_threshold: Optional[int] = None,
        conflict: Optional[ConflictMode] = None,
        if_match: Optional[str] = None,
        hash_algorithm: HashAlgorithm = "sha256",
        use_auto_chunk_size: Optional[bool] = None,
    ) -> DriveFile:
        # Files >= 1 GiB always go chunked (API / reliability)
        resolved = self.resolve_chunk_size(chunk_size, use_auto_chunk_size=use_auto_chunk_size)
        threshold = self.resolve_chunk_threshold(
            chunk_threshold, use_auto_chunk_size=use_auto_chunk_size
        )
        if file.total_size >= ONE_GB or file.total_size > threshold:
            return self.upload_chunked(
                file,
                chunk_size=resolved,
                conflict=conflict,
                if_match=if_match,
                hash_algorithm=hash_algorithm,
            )
        return self.upload_direct(file, conflict=conflict, if_match=if_match)

    def upload_direct(
        self,
        file: KDriveFile,
        *,
        conflict: Optional[ConflictMode] = None,
        if_match: Optional[str] = None,
    ) -> DriveFile:
        self._raise_if_cancelled()
        params: Dict[str, Any] = {
            "file_name": file.name,
            "total_size": file.total_size,
        }
        params.update(file.upload_timing_params())
        if file.directory_path is not None:
            params["directory_path"] = file.directory_path
        if file.directory_id is not None:
            params["directory_id"] = file.directory_id
        if file.file_id is not None:
            params["file_id"] = file.file_id
        if conflict is not None:
            params["conflict"] = self.enum_value(conflict)

        headers = {"If-Match": if_match} if if_match else None
        file.content.seek(0)
        payload = self.json_request(
            "POST",
            self.url(3, "upload"),
            params=self.as_params(params),
            data=file.content,
            headers=headers,
        )
        return self.parse_upload_result(self.data(payload))

    def upload_chunked(
        self,
        file: KDriveFile,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        *,
        conflict: Optional[ConflictMode] = None,
        if_match: Optional[str] = None,
        hash_algorithm: HashAlgorithm = "sha256",
    ) -> DriveFile:
        algo_name, hasher_factory = _resolve_hasher(hash_algorithm)
        total_chunks = max(1, (file.total_size + chunk_size - 1) // chunk_size)
        start_payload: Dict[str, Any] = {
            "file_name": file.name,
            "total_size": file.total_size,
            "total_chunks": total_chunks,
        }
        start_payload.update(file.upload_timing_params())
        if file.directory_path is not None:
            start_payload["directory_path"] = file.directory_path
        if file.directory_id is not None:
            start_payload["directory_id"] = file.directory_id
        if file.file_id is not None:
            start_payload["file_id"] = file.file_id
        if conflict is not None:
            start_payload["conflict"] = self.enum_value(conflict)

        self._raise_if_cancelled()
        headers = {"If-Match": if_match} if if_match else None
        start_json = self.json_request(
            "POST",
            self.url(3, "upload/session/start"),
            json=start_payload,
            headers=headers,
        )
        session = UploadSession.from_dict(self.data(start_json) or {})

        file.content.seek(0)
        chunk_digests: List[bytes] = []
        uploaded = 0
        progress_lock = threading.Lock()
        workers = self.compute_upload_workers(chunk_size=chunk_size, total_chunks=total_chunks)

        def _send_chunk(item: tuple) -> int:
            self._raise_if_cancelled()
            _number, data, params = item
            chunk_res = self.request(
                "POST",
                session.upload_url,
                params=params,
                data=data,
            )
            self.handle_json(chunk_res)
            return len(data)

        def _flush_batch(batch: List[tuple]) -> None:
            nonlocal uploaded
            if not batch:
                return
            if len(batch) == 1 or workers == 1:
                for item in batch:
                    size = _send_chunk(item)
                    uploaded += size
                    if self.progress_callback and file.total_size:
                        self.progress_callback(uploaded * 100 / file.total_size)
                return
            with ThreadPoolExecutor(max_workers=min(workers, len(batch))) as executor:
                futures = [executor.submit(_send_chunk, item) for item in batch]
                for future in as_completed(futures):
                    size = future.result()
                    with progress_lock:
                        uploaded += size
                        if self.progress_callback and file.total_size:
                            self.progress_callback(uploaded * 100 / file.total_size)

        batch: List[tuple] = []
        chunk_num = 1
        while True:
            chunk = file.content.read(chunk_size)
            if not chunk:
                break
            hasher = hasher_factory()
            hasher.update(chunk)
            digest = hasher.digest()
            chunk_digests.append(digest)
            batch.append(
                (
                    chunk_num,
                    chunk,
                    {
                        "chunk_number": chunk_num,
                        "chunk_size": len(chunk),
                        "chunk_hash": f"{algo_name}:{digest.hex()}",
                    },
                )
            )
            chunk_num += 1
            if len(batch) >= workers:
                _flush_batch(batch)
                batch = []
        _flush_batch(batch)

        total_hasher = hasher_factory()
        for digest in chunk_digests:
            total_hasher.update(digest)

        finish_payload = {"total_chunk_hash": f"{algo_name}:{total_hasher.hexdigest()}"}
        finish_json = self.json_request(
            "POST",
            self.url(3, f"upload/session/{session.token}/finish"),
            json=finish_payload,
        )
        return self.parse_upload_result(self.data(finish_json))

    def upload_batch(
        self,
        files: Sequence[KDriveFile],
        *,
        conflict: Optional[ConflictMode] = None,
        chunk_size: Optional[int] = None,
        use_auto_chunk_size: Optional[bool] = None,
        hash_algorithm: HashAlgorithm = "sha256",
        max_workers: Optional[int] = None,
    ) -> List[DriveFile]:
        """Upload multiple files; tries API batch session, falls back to parallel uploads."""
        file_list = list(files)
        if not file_list:
            return []

        resolved = self.resolve_chunk_size(chunk_size, use_auto_chunk_size=use_auto_chunk_size)
        try:
            return self._upload_batch_via_sessions(
                file_list,
                conflict=conflict,
                chunk_size=resolved,
                hash_algorithm=hash_algorithm,
            )
        except Exception:
            workers = max(1, max_workers or self.parallelism)
            results: List[Optional[DriveFile]] = [None] * len(file_list)
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(
                        self.upload,
                        f,
                        chunk_size=resolved,
                        conflict=conflict,
                        hash_algorithm=hash_algorithm,
                        use_auto_chunk_size=False,
                    ): idx
                    for idx, f in enumerate(file_list)
                }
                for future in as_completed(futures):
                    results[futures[future]] = future.result()
            return [r for r in results if r is not None]

    def _upload_batch_via_sessions(
        self,
        files: List[KDriveFile],
        *,
        conflict: Optional[ConflictMode],
        chunk_size: int,
        hash_algorithm: HashAlgorithm,
    ) -> List[DriveFile]:
        body_files = []
        for f in files:
            entry: Dict[str, Any] = {
                "file_name": f.name,
                "total_size": f.total_size,
                "total_chunks": max(1, (f.total_size + chunk_size - 1) // chunk_size),
            }
            if f.directory_id is not None:
                entry["directory_id"] = f.directory_id
            if f.directory_path is not None:
                entry["directory_path"] = f.directory_path
            if f.file_id is not None:
                entry["file_id"] = f.file_id
            if conflict is not None:
                entry["conflict"] = self.enum_value(conflict)
            body_files.append(entry)

        start = self.start_upload_session_batch({"files": body_files})
        sessions_raw = self.data(start) or start
        if isinstance(sessions_raw, dict):
            sessions_raw = sessions_raw.get("sessions") or sessions_raw.get("files") or [sessions_raw]
        if not isinstance(sessions_raw, list) or len(sessions_raw) != len(files):
            raise RuntimeError("Unexpected batch start payload")

        results: List[DriveFile] = []
        tokens: List[str] = []
        for file, session_data in zip(files, sessions_raw):
            if not isinstance(session_data, dict):
                raise RuntimeError("Invalid session in batch response")
            session = UploadSession.from_dict(session_data)
            tokens.append(session.token)
            # Reuse single-file chunked path by temporarily swapping start — upload via session fields
            results.append(
                self._upload_chunks_to_session(
                    file,
                    session,
                    chunk_size=chunk_size,
                    hash_algorithm=hash_algorithm,
                )
            )

        finish_body = {"tokens": tokens}
        try:
            self.finish_upload_session_batch(finish_body)
        except Exception:
            # Individual finishes already done in _upload_chunks_to_session
            pass
        return results

    def _upload_chunks_to_session(
        self,
        file: KDriveFile,
        session: UploadSession,
        *,
        chunk_size: int,
        hash_algorithm: HashAlgorithm,
    ) -> DriveFile:
        algo_name, hasher_factory = _resolve_hasher(hash_algorithm)
        file.content.seek(0)
        digests: List[bytes] = []
        chunk_num = 1
        while True:
            chunk = file.content.read(chunk_size)
            if not chunk:
                break
            hasher = hasher_factory()
            hasher.update(chunk)
            digest = hasher.digest()
            digests.append(digest)
            params = {
                "chunk_number": chunk_num,
                "chunk_size": len(chunk),
                "chunk_hash": f"{algo_name}:{digest.hex()}",
            }
            chunk_res = self.request("POST", session.upload_url, params=params, data=chunk)
            self.handle_json(chunk_res)
            chunk_num += 1

        total_hasher = hasher_factory()
        for digest in digests:
            total_hasher.update(digest)
        finish = self.json_request(
            "POST",
            self.url(3, f"upload/session/{session.token}/finish"),
            json={"total_chunk_hash": f"{algo_name}:{total_hasher.hexdigest()}"},
        )
        return self.parse_upload_result(self.data(finish))

    def cancel_upload_session(self, session_token: str) -> bool:
        payload = self.json_request(
            "DELETE",
            self.url(3, f"upload/session/{session_token}"),
        )
        return bool(self.data(payload))

    def cancel_upload_sessions_batch(
        self,
        tokens: Sequence[str],
    ) -> bool:
        payload = self.json_request(
            "DELETE",
            self.url(3, "upload/session/batch"),
            json={"tokens": list(tokens)},
        )
        data = self.data(payload)
        return True if data is None else bool(data)

    def cancel_upload_by_path(
        self,
        *,
        directory_id: Optional[Union[str, int]] = None,
        directory_path: Optional[str] = None,
        file_id: Optional[Union[str, int]] = None,
        file_name: Optional[str] = None,
    ) -> bool:
        body: Dict[str, Any] = {}
        if directory_id is not None:
            body["directory_id"] = directory_id
        if directory_path is not None:
            body["directory_path"] = directory_path
        if file_id is not None:
            body["file_id"] = file_id
        if file_name is not None:
            body["file_name"] = file_name
        payload = self.json_request(
            "DELETE",
            self.url(2, "upload"),
            json=body or None,
        )
        data = self.data(payload)
        return True if data is None else bool(data)

    def start_upload_session_batch(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.json_request(
            "POST",
            self.url(3, "upload/session/batch/start"),
            json=body,
        )

    def finish_upload_session_batch(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.json_request(
            "POST",
            self.url(3, "upload/session/batch/finish"),
            json=body,
        )
