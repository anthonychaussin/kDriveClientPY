"""kdrive_client to use kDrive API"""

import io
import os
import random
import time
from threading import Lock
from typing import BinaryIO, Tuple

import requests

from kdrive_client.kdrive_api_error import KDriveApiError
from kdrive_client.kdrive_file import KDriveFile


class KDriveClient:
    """Represents a client to upload files to kDrive."""

    base_url: str = "https://api.infomaniak.com"
    session = requests.Session()

    def __init__(
            self,
            token: str,
            drive_id: int,
            auto_chunk: bool = True,
    ) -> None:
        self.dynamic_chunk_size = 0
        self.direct_upload_threshold = 0
        self.drive_id = drive_id
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self._rate_limit_lock = Lock()
        self._rate_limit_reset = time.time()
        self._rate_limit_count = 0

        if auto_chunk:
            self.initialize_upload_strategy()

    # -------------------------- Helpers --------------------------
    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Helper method to make a request to kDrive."""
        self._apply_rate_limit()
        if not url.startswith("https"):
            url = self.base_url + url
        resp = self.session.request(method, url, **kwargs)
        if not resp.ok:
            try:
                data = resp.json()
                detail = data.get("error")
                if detail:
                    raise (KDriveApiError(
                        f"{detail.get('code')}: {detail.get('description')}",
                        data,
                        **kwargs
                    ))
            except KDriveApiError:
                resp.raise_for_status()
            resp.raise_for_status()
        return resp

    def _apply_rate_limit(self):
        """Define a rate limit for uploading files."""

        with self._rate_limit_lock:
            now = time.time()
            if now > self._rate_limit_reset + 60:
                self._rate_limit_count = 0
                self._rate_limit_reset = now
            if self._rate_limit_count >= 60:
                sleep_time = (self._rate_limit_reset + 60) - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self._rate_limit_count = 0
                self._rate_limit_reset = time.time()
            self._rate_limit_count += 1

    # -------------------------- Upload --------------------------
    def upload(self, file: KDriveFile, directory_path: str = None, directory_id: int = None,
               conflict_choice="rename") -> dict:
        """Upload a file to kDrive."""

        if not directory_path and not directory_id:
            raise ValueError("File path and id cannot be null together")

        file.prepare(self.dynamic_chunk_size)

        if file.total_size >= 1 * 1024 * 1024 * 1024:  # ≥ 1 GB → forced chunked
            return self._upload_chunked(
                file,
                conflict_choice,
                directory_id=directory_id,
                directory_path=directory_path)
        # ≤ 1 MB or network fast enough
        if file.total_size <= 1 * 1024 * 1024 or file.total_size <= self.direct_upload_threshold:
            return self._upload_direct(
                file,
                conflict_choice,
                directory_id=directory_id,
                directory_path=directory_path)

        return self._upload_chunked(
            file,
            conflict_choice,
            directory_id=directory_id,
            directory_path=directory_path)

    def _upload_direct(
            self,
            file: KDriveFile,
            conflict_choice: str,
            directory_id: int,
            directory_path: str) -> dict:
        """Upload a file to kDrive."""

        with open(file.path, "rb") as fh:
            params = file.file_params(directory_id=directory_id, directory_path=directory_path)
            params["total_size"] = os.path.getsize(file.path)
            params["conflict"] = conflict_choice
            url = f"/3/drive/{self.drive_id}/upload"
            resp = self._request("POST", url, params=params, data=fh)
        return resp.json().get("data")

    def _start_session(self, file: KDriveFile, conflict_choice: str, directory_id: int,
                       directory_path: str) -> Tuple[str, str]:
        """Start a session."""

        params = file.file_params(directory_id=directory_id, directory_path=directory_path)
        params["total_size"] = file.total_size
        params["total_hash"] = "sha256:" + file.get_total_hash()
        params["total_chunks"] = len(file.chunks)
        params["conflict"] = conflict_choice
        body = params
        url = f"/3/drive/{self.drive_id}/upload/session/start"
        data = self._request("POST", url, json=body).json()
        token = data.get("data", {}).get("token")
        upload_url = data.get("data", {}).get("upload_url")

        if not token or not upload_url:
            raise KDriveApiError("Invalid start session response", data)

        return token, upload_url

    def _upload_chunked(
            self,
            file: KDriveFile,
            conflict_choice: str,
            directory_id: int,
            directory_path: str) -> dict:
        """Make a chunked upload request to kDrive."""

        token, upload_url = self._start_session(file, conflict_choice, directory_id=directory_id,
                                                directory_path=directory_path)
        url = f"{upload_url}/3/drive/{self.drive_id}/upload/session/{token}/chunk"

        for chunk in file.chunks:
            params = {
                "chunk_number": chunk.index,
                "chunk_size": chunk.size,
                "chunk_hash": "sha256:" + chunk.get_hash(),
            }
            try:
                self._request("POST", url, params=params, data=chunk.content)
            except Exception as e:
                self.cancel_upload_session(token)
                raise KDriveApiError(f"Error uploading chunk : {str(e)}", False) from e

        return self.finish_upload_session(token, file.get_total_hash())

    # -------------------------- Download --------------------------
    def download_to(self, file_id: int, dest: BinaryIO) -> None:
        """Download a file from kDrive."""

        url = f"/2/drive/{self.drive_id}/files/{file_id}/download"
        with self._request("GET", url, stream=True) as resp:
            for chunk in resp.iter_content(1024 * 64):
                if chunk:
                    dest.write(chunk)

    def download(self, file_id: int) -> bytes:
        """Download a file from kDrive."""

        buf = io.BytesIO()
        self.download_to(file_id, buf)
        return buf.getvalue()

    def initialize_upload_strategy(self) -> None:
        """Initialize upload strategy."""

        dummy_data = bytes(random.getrandbits(8) for _ in range(1024 * 1024))  # 1MB
        body = {
            "file_name": "speedtest.dat",
            "total_size": len(dummy_data),
            "total_chunks": 1,
            "directory_path": "/Private",
            "conflict": "rename",
        }

        start_resp = self._request("POST", f"/3/drive/{self.drive_id}/upload/session/start", json=body)
        data = start_resp.json()["data"]
        token = data["token"]
        upload_url = data["upload_url"]

        chunk_url = f"{upload_url}/3/drive/{self.drive_id}/upload/session/{token}/chunk"
        params = {
            "chunk_number": 1,
            "chunk_size": len(dummy_data),
        }

        start = time.perf_counter()
        self._request("POST", chunk_url, params=params, data=dummy_data)
        elapsed = time.perf_counter() - start

        cancel_url = f"/2/drive/{self.drive_id}/upload/session/{token}"
        self._request("DELETE", cancel_url)

        speed_bps = len(dummy_data) / elapsed
        self.direct_upload_threshold = int(speed_bps)
        self.dynamic_chunk_size = int(speed_bps * 0.9)

    def cancel_upload_session(self, token: str) -> dict:
        """Cancel an upload session."""

        url = f"/2/drive/{self.drive_id}/upload/session/{token}"
        return self._request("DELETE", url).json()

    def finish_upload_session(self, token: str, total_chunk_hash: str) -> dict:
        """Finish an upload session."""

        url = f"/3/drive/{self.drive_id}/upload/session/{token}/finish"
        body = {"total_chunk_hash": f"sha256:{total_chunk_hash}"}
        resp = self._request("POST", url, json=body)
        return resp.json().get("data")["file"]
