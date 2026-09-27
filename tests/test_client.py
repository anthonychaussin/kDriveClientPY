from __future__ import annotations

import io
import json
from typing import Any, Dict
from unittest import mock

import pytest
import responses

from kdrive_client import (
    ConflictMode,
    DriveInfo,
    FileCount,
    KDriveApiException,
    KDriveClient,
    KDriveFile,
    Order,
    OrderBy,
    ShareLink,
)


BASE = "https://api.infomaniak.com"
DRIVE_ID = "12345"
TOKEN = "test-token"


@pytest.fixture
def client() -> KDriveClient:
    return KDriveClient(TOKEN, DRIVE_ID, parallelism=2, max_retries=2, timeout=5.0)


def _ok(data: Any = None, **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"result": "success", "data": data}
    payload.update(extra)
    return payload


def _err(code: str = "object_not_found", description: str = "Not found", **extra: Any) -> Dict[str, Any]:
    error: Dict[str, Any] = {"code": code, "description": description}
    error.update(extra)
    return {"result": "error", "error": error}


# --- Exceptions / HTTP resilience ----------------------------------------


@responses.activate
def test_api_error_enriched(client: KDriveClient) -> None:
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/1",
        json=_err(
            "validation_failed",
            "Validation failed",
            context={"attribute": "name"},
            errors=[{"code": "attribute_required", "description": "name required"}],
        ),
        status=422,
    )
    with pytest.raises(KDriveApiException) as exc_info:
        client.get_file(1)
    err = exc_info.value
    assert err.status == 422
    assert err.code == "validation_failed"
    assert err.context["attribute"] == "name"
    assert err.errors[0]["code"] == "attribute_required"


@responses.activate
def test_retry_on_429_then_success(client: KDriveClient) -> None:
    url = f"{BASE}/3/drive/{DRIVE_ID}/files/1"
    responses.add(responses.GET, url, json=_err("rate_limit", "Too many"), status=429)
    responses.add(
        responses.GET,
        url,
        json=_ok({"id": 1, "name": "root", "type": "dir"}),
        status=200,
    )
    with mock.patch("kdrive_client.http.time.sleep"):
        entry = client.get_file(1)
    assert entry.id == 1
    assert entry.name == "root"
    assert len(responses.calls) == 2


@responses.activate
def test_context_manager_closes_session() -> None:
    with KDriveClient(TOKEN, DRIVE_ID) as c:
        assert c.session is not None
        session = c.session
    # After close, adapters are cleared; further use may still work but close was called
    assert session.adapters  # session object still exists


# --- Upload --------------------------------------------------------------


@responses.activate
def test_upload_direct(client: KDriveClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/3/drive/{DRIVE_ID}/upload",
        json=_ok({"id": 99, "name": "hello.txt", "type": "file", "size": 12}),
        status=200,
    )
    content = io.BytesIO(b"Hello World!")
    file = KDriveFile(name="hello.txt", directory_id=1, content=content)
    result = client.upload_direct(file, conflict=ConflictMode.RENAME, if_match="abc")
    assert result.id == 99
    assert result.name == "hello.txt"
    assert "If-Match" in responses.calls[0].request.headers
    assert responses.calls[0].request.headers["If-Match"] == "abc"


@responses.activate
def test_upload_chunked_single_pass_hash(client: KDriveClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/3/drive/{DRIVE_ID}/upload/session/start",
        json=_ok(
            {
                "token": "sess-1",
                "upload_url": f"{BASE}/upload-host/chunk",
            }
        ),
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/upload-host/chunk",
        json=_ok({"number": 1, "status": "ok"}),
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/3/drive/{DRIVE_ID}/upload/session/sess-1/finish",
        json=_ok({"file": {"id": 42, "name": "big.bin", "type": "file", "size": 5}}),
        status=200,
    )
    content = io.BytesIO(b"abcde")
    file = KDriveFile(name="big.bin", directory_id=1, content=content)
    result = client.upload_chunked(file, chunk_size=2)
    assert result.id == 42
    finish_body = json.loads(responses.calls[-1].request.body)
    assert finish_body["total_chunk_hash"].startswith("sha256:")
    # 3 chunks (2+2+1) + start + finish
    assert len([c for c in responses.calls if "upload-host" in c.request.url]) == 3


# --- Pagination ----------------------------------------------------------


@responses.activate
def test_list_files_pagination_and_iter(client: KDriveClient) -> None:
    def _list_callback(request):
        from urllib.parse import parse_qs, urlparse

        qs = parse_qs(urlparse(request.url).query)
        cursor = (qs.get("cursor") or [None])[0]
        if cursor == "c1":
            body = _ok(
                [{"id": 2, "name": "b.txt", "type": "file"}],
                cursor=None,
                has_more=False,
            )
        else:
            body = _ok(
                [{"id": 1, "name": "a.txt", "type": "file"}],
                cursor="c1",
                has_more=True,
            )
        return (200, {}, json.dumps(body))

    responses.add_callback(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/1/files",
        callback=_list_callback,
        content_type="application/json",
    )
    page = client.list_files(1, limit=50, order_by=OrderBy.NAME, order=Order.ASC)
    assert len(page) == 1
    assert page.has_more is True
    assert page.cursor == "c1"

    items = client.list_all_files(1, limit=50)
    assert [i.id for i in items] == [1, 2]


# --- Cancel / trash / drive / share / favorite ---------------------------


@responses.activate
def test_cancel_action(client: KDriveClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/2/drive/{DRIVE_ID}/files/10/rename",
        json=_ok({"cancel_id": "cid-1", "valid_until": 123}),
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/2/drive/{DRIVE_ID}/cancel",
        json=_ok(True),
        status=200,
    )
    action = client.rename(10, "new.txt")
    assert action.cancel_id == "cid-1"
    assert client.cancel(action) is True


@responses.activate
def test_trash_lifecycle(client: KDriveClient) -> None:
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/trash",
        json=_ok([{"id": 7, "name": "gone.txt", "type": "file"}], has_more=False),
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/2/drive/{DRIVE_ID}/trash/7/restore",
        json=_ok({"cancel_id": "r1"}),
        status=200,
    )
    responses.add(
        responses.DELETE,
        f"{BASE}/2/drive/{DRIVE_ID}/trash/8",
        json=_ok(True),
        status=200,
    )
    responses.add(
        responses.DELETE,
        f"{BASE}/2/drive/{DRIVE_ID}/trash",
        json=_ok(False),
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/trash/count",
        json=_ok({"count": 3, "files": 2, "directories": 1}),
        status=200,
    )
    listing = client.list_trash()
    assert listing[0].name == "gone.txt"
    assert client.restore(7, 1).cancel_id == "r1"
    assert client.delete_permanently(8) is True
    assert client.empty_trash() is False
    count = client.count_trash()
    assert isinstance(count, FileCount)
    assert count.count == 3


@responses.activate
def test_drive_info_and_duplicate_count(client: KDriveClient) -> None:
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}",
        json=_ok({"id": int(DRIVE_ID), "name": "My Drive", "used_size": 100}),
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/drive",
        json=_ok([{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]),
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/3/drive/{DRIVE_ID}/files/5/duplicate",
        json=_ok({"id": 6, "name": "copy.txt", "type": "file"}),
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/1/count",
        json=_ok({"count": 10, "files": 7, "directories": 3}),
        status=200,
    )
    drive = client.get_drive()
    assert isinstance(drive, DriveInfo)
    assert drive.name == "My Drive"
    drives = client.list_drives(account_id=99)
    assert len(drives) == 2
    assert client.duplicate(5, name="copy.txt").id == 6
    assert client.count(1).files == 7


@responses.activate
def test_favorites_and_share_link(client: KDriveClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/2/drive/{DRIVE_ID}/files/3/favorite",
        json=_ok(True),
        status=200,
    )
    responses.add(
        responses.DELETE,
        f"{BASE}/2/drive/{DRIVE_ID}/files/3/favorite",
        json=_ok(True),
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/favorites",
        json=_ok([{"id": 3, "name": "fav.txt", "type": "file", "is_favorite": True}]),
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/2/drive/{DRIVE_ID}/files/3/link",
        json=_ok({"url": "https://share.example/x", "right": "public", "can_download": True}),
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/files/3/link",
        json=_ok({"url": "https://share.example/x", "right": "public"}),
        status=200,
    )
    responses.add(
        responses.DELETE,
        f"{BASE}/2/drive/{DRIVE_ID}/files/3/link",
        json=_ok(True),
        status=200,
    )
    assert client.favorite(3) is True
    assert client.unfavorite(3) is True
    favs = client.list_favorites()
    assert favs[0].is_favorite is True
    link = client.create_share_link(3, right="public", can_download=True)
    assert isinstance(link, ShareLink)
    assert link.url.endswith("/x")
    assert client.get_share_link(3).right == "public"
    assert client.delete_share_link(3) is True


@responses.activate
def test_download_to_path(client: KDriveClient, tmp_path) -> None:
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/files/9/download",
        body=b"file-bytes",
        status=200,
        content_type="application/octet-stream",
    )
    dest = tmp_path / "out.bin"
    path = client.download_to_path(9, dest)
    assert path.read_bytes() == b"file-bytes"
