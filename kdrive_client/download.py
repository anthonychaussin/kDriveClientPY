from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional, Union

JsonDict = Dict[str, Any]


def _password_headers(password: Optional[str]) -> Optional[Dict[str, str]]:
    if password is None:
        return None
    return {"x-kdrive-file-password": password}


class DownloadMixin:
    """File download, preview, thumbnail, archive, and temporary URL endpoints."""

    download_progress_callback: Optional[Callable[[float], None]]

    def download(
        self,
        file_id: Union[str, int],
        *,
        as_format: Optional[str] = None,
        password: Optional[str] = None,
        use_temporary_url: bool = False,
        expected_hash: Optional[str] = None,
        total_size: Optional[int] = None,
    ) -> bytes:
        if use_temporary_url:
            data = self.get_temporary_url(file_id)
            url = data if isinstance(data, str) else (data.get("url") or data.get("temporary_url"))
            if not isinstance(url, str):
                raise ValueError("temporary_url response missing url")
            response = self.request("GET", url, allow_redirects=True, binary=True)
            content = self.handle_binary(response)
        else:
            params = {"as": as_format} if as_format else None
            response = self.request(
                "GET",
                self.url(2, f"files/{file_id}/download"),
                params=params,
                headers=_password_headers(password),
                allow_redirects=True,
                binary=True,
            )
            content = self.handle_binary(response)
        self._verify_hash(content, expected_hash)
        callback = getattr(self, "download_progress_callback", None)
        if callback:
            callback(100.0)
        return content

    def download_iter(
        self,
        file_id: Union[str, int],
        *,
        as_format: Optional[str] = None,
        chunk_size: int = 1024 * 1024,
        password: Optional[str] = None,
        total_size: Optional[int] = None,
    ) -> Iterator[bytes]:
        params = {"as": as_format} if as_format else None
        response = self.request(
            "GET",
            self.url(2, f"files/{file_id}/download"),
            params=params,
            headers=_password_headers(password),
            allow_redirects=True,
            stream=True,
            binary=True,
        )
        if not response.ok:
            self.raise_api_error(response)
        known_total = total_size
        if known_total is None:
            cl = response.headers.get("Content-Length")
            if cl and cl.isdigit():
                known_total = int(cl)
        downloaded = 0
        callback = getattr(self, "download_progress_callback", None)
        try:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    downloaded += len(chunk)
                    if callback and known_total:
                        callback(min(100.0, downloaded * 100 / known_total))
                    elif callback:
                        callback(float(downloaded))
                    yield chunk
            if callback and known_total:
                callback(100.0)
        finally:
            response.close()

    def download_to_path(
        self,
        file_id: Union[str, int],
        destination: Union[str, Path],
        *,
        as_format: Optional[str] = None,
        chunk_size: int = 1024 * 1024,
        password: Optional[str] = None,
        use_temporary_url: bool = False,
        expected_hash: Optional[str] = None,
        total_size: Optional[int] = None,
    ) -> Path:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        if use_temporary_url:
            data = self.download(
                file_id,
                as_format=as_format,
                password=password,
                use_temporary_url=True,
                expected_hash=expected_hash,
                total_size=total_size,
            )
            path.write_bytes(data)
            return path
        hasher = hashlib.sha256() if expected_hash else None
        with path.open("wb") as handle:
            for chunk in self.download_iter(
                file_id,
                as_format=as_format,
                chunk_size=chunk_size,
                password=password,
                total_size=total_size,
            ):
                handle.write(chunk)
                if hasher is not None:
                    hasher.update(chunk)
        if hasher is not None and expected_hash:
            self._verify_hash_digest(hasher.hexdigest(), expected_hash)
        return path

    @staticmethod
    def _verify_hash(content: bytes, expected_hash: Optional[str]) -> None:
        if not expected_hash:
            return
        digest = hashlib.sha256(content).hexdigest()
        DownloadMixin._verify_hash_digest(digest, expected_hash)

    @staticmethod
    def _verify_hash_digest(digest: str, expected_hash: str) -> None:
        expected = expected_hash.split(":", 1)[-1].lower()
        if digest.lower() != expected:
            raise ValueError(f"Hash mismatch: expected {expected_hash}, got sha256:{digest}")

    def download_preview(
        self,
        file_id: Union[str, int],
        *,
        password: Optional[str] = None,
        **query: Any,
    ) -> bytes:
        response = self.request(
            "GET",
            self.url(2, f"files/{file_id}/preview"),
            params=self.as_params(query) or None,
            headers=_password_headers(password),
            allow_redirects=True,
            binary=True,
        )
        return self.handle_binary(response)

    def download_thumbnail(self, file_id: Union[str, int]) -> bytes:
        response = self.request(
            "GET",
            self.url(2, f"files/{file_id}/thumbnail"),
            allow_redirects=True,
            binary=True,
        )
        return self.handle_binary(response)

    def download_trash_thumbnail(self, file_id: Union[str, int]) -> bytes:
        response = self.request(
            "GET",
            self.url(2, f"trash/{file_id}/thumbnail"),
            allow_redirects=True,
            binary=True,
        )
        return self.handle_binary(response)

    def download_version(
        self,
        file_id: Union[str, int],
        version_id: Union[str, int],
        *,
        password: Optional[str] = None,
    ) -> bytes:
        response = self.request(
            "GET",
            self.url(2, f"files/{file_id}/versions/{version_id}/download"),
            headers=_password_headers(password),
            allow_redirects=True,
            binary=True,
        )
        return self.handle_binary(response)

    def download_archive(self, uuid: str) -> bytes:
        response = self.request(
            "GET",
            self.url(2, f"files/archives/{uuid}"),
            allow_redirects=True,
            binary=True,
        )
        return self.handle_binary(response)

    def get_archive_status(self, uuid: str) -> Dict[str, Any]:
        payload = self.json_request("GET", self.url(2, f"files/archives/{uuid}"))
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data, **payload}

    def build_and_download_archive(
        self,
        body: Dict[str, Any],
        *,
        timeout: float = 300.0,
        poll_interval: float = 1.0,
        destination: Optional[Union[str, Path]] = None,
    ) -> Union[bytes, Path]:
        built = self.build_archive(body)
        uuid = built.get("uuid") or built.get("id") or (built.get("data") or {}).get("uuid")
        if not uuid:
            raise ValueError("build_archive response missing uuid")

        failed = {"error", "failed"}

        def _try_download() -> Optional[bytes]:
            try:
                return self.download_archive(str(uuid))
            except Exception:
                try:
                    status = self.get_archive_status(str(uuid))
                    state = str(status.get("status") or status.get("state") or "").lower()
                    if state in failed:
                        raise RuntimeError(f"Archive {uuid} failed: {status}")
                except RuntimeError:
                    raise
                except Exception:
                    pass
                return None

        wait = getattr(self, "wait_for_async_result", None)
        if callable(wait):
            content = wait(
                _try_download,
                timeout=timeout,
                poll_interval=poll_interval,
                is_done=lambda value: value is not None,
            )
        else:
            deadline = time.monotonic() + timeout
            content = None
            while time.monotonic() < deadline:
                content = _try_download()
                if content is not None:
                    break
                time.sleep(max(0.05, poll_interval))
            if content is None:
                content = self.download_archive(str(uuid))

        if not isinstance(content, (bytes, bytearray)):
            content = self.download_archive(str(uuid))
        if destination is not None:
            path = Path(destination)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            return path
        return content

    def get_temporary_url(
        self,
        file_id: Union[str, int],
        *,
        duration: Optional[int] = None,
    ) -> Union[str, Dict[str, Any]]:
        params = self.as_params({"duration": duration})
        payload = self.json_request(
            "GET",
            self.url(2, f"files/{file_id}/temporary_url"),
            params=params or None,
        )
        data = self.data(payload)
        if isinstance(data, dict):
            url = data.get("temporary_url") or data.get("url")
            return url if isinstance(url, str) else data
        if isinstance(data, str):
            return data
        return payload
