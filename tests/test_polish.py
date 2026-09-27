from __future__ import annotations

import io
from unittest import mock

import pytest
import responses

from kdrive_client import (
    AccessUser,
    Category,
    ExternalImport,
    KDriveClient,
    KDriveFile,
    suggest_chunk_size,
)


BASE = "https://api.infomaniak.com"
DRIVE_ID = "12345"
TOKEN = "test-token"


@pytest.fixture
def client() -> KDriveClient:
    return KDriveClient(TOKEN, DRIVE_ID, parallelism=2, max_retries=0, timeout=5.0)


def test_suggest_chunk_size_bounds():
    assert suggest_chunk_size(0) == 1024 * 1024
    assert suggest_chunk_size(100_000_000, parallelism=4) >= 1024 * 1024
    assert suggest_chunk_size(100_000_000, parallelism=4) <= 100 * 1024 * 1024


@responses.activate
def test_upload_batch_fallback(client: KDriveClient) -> None:
    # Batch start fails → parallel individual uploads
    responses.add(
        responses.POST,
        f"{BASE}/3/drive/{DRIVE_ID}/upload/session/batch/start",
        json={"result": "error", "error": {"code": "not_supported", "description": "x"}},
        status=400,
    )
    responses.add(
        responses.POST,
        f"{BASE}/3/drive/{DRIVE_ID}/upload",
        json={"result": "success", "data": {"id": 1, "name": "a.txt", "type": "file"}},
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/3/drive/{DRIVE_ID}/upload",
        json={"result": "success", "data": {"id": 2, "name": "b.txt", "type": "file"}},
        status=200,
    )
    files = [
        KDriveFile(name="a.txt", directory_id=1, content=io.BytesIO(b"a")),
        KDriveFile(name="b.txt", directory_id=1, content=io.BytesIO(b"b")),
    ]
    results = client.upload_batch(files)
    assert [r.id for r in results] == [1, 2]


@responses.activate
def test_cancel_upload_sessions_batch(client: KDriveClient) -> None:
    responses.add(
        responses.DELETE,
        f"{BASE}/3/drive/{DRIVE_ID}/upload/session/batch",
        json={"result": "success", "data": True},
        status=200,
    )
    assert client.cancel_upload_sessions_batch(["t1", "t2"]) is True


@responses.activate
def test_build_and_download_archive(client: KDriveClient, tmp_path) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/3/drive/{DRIVE_ID}/files/archives",
        json={"result": "success", "data": {"uuid": "arch-9"}},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/files/archives/arch-9",
        body=b"ZIPDATA",
        status=200,
        content_type="application/octet-stream",
    )
    dest = tmp_path / "out.zip"
    path = client.build_and_download_archive({"file_ids": [1]}, destination=dest, timeout=5)
    assert path.read_bytes() == b"ZIPDATA"


@responses.activate
def test_share_link_archive(client: KDriveClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/2/app/{DRIVE_ID}/share/suuid/archive",
        json={"result": "success", "data": {"uuid": "auuid"}},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/app/{DRIVE_ID}/share/suuid/archive/auuid/download",
        body=b"sharezip",
        status=200,
    )
    meta = client.create_share_link_archive("suuid")
    assert meta.get("uuid") == "auuid"
    assert client.download_share_link_archive("suuid", "auuid") == b"sharezip"


@responses.activate
def test_download_expected_hash(client: KDriveClient) -> None:
    import hashlib

    body = b"hello-hash"
    digest = hashlib.sha256(body).hexdigest()
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/files/9/download",
        body=body,
        status=200,
    )
    assert client.download(9, expected_hash=f"sha256:{digest}") == body
    with pytest.raises(ValueError):
        client.download(9, expected_hash="sha256:deadbeef")


@responses.activate
def test_smart_find_trash_and_undo_multi(client: KDriveClient) -> None:
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/trash",
        json={
            "result": "success",
            "data": [{"id": 4, "name": "gone.txt", "type": "file"}],
            "has_more": False,
        },
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/2/drive/{DRIVE_ID}/cancel",
        json={"result": "success", "data": True},
        status=200,
    )
    found = client.find_trash_item("gone.txt")
    assert found is not None and found.id == 4
    assert client.undo(cancel_ids=["a", "b"]) is True


@responses.activate
def test_wait_for_import_and_niche(client: KDriveClient) -> None:
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/imports/3",
        json={"result": "success", "data": {"id": 3, "status": "running"}},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/imports/3",
        json={"result": "success", "data": {"id": 3, "status": "done"}},
        status=200,
    )
    responses.add(
        responses.DELETE,
        f"{BASE}/2/drive/{DRIVE_ID}/files/1/categories",
        json={"result": "success", "data": True},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/statistics/activities",
        json={"result": "success", "data": {"count": 1}},
        status=200,
    )
    with mock.patch("kdrive_client.smart.time.sleep"):
        result = client.wait_for_import_complete(3, timeout=5, poll_interval=0.01)
    assert result["status"] == "done"
    assert client.remove_all_categories(1) is True
    assert client.get_activity_statistics()["count"] == 1


def test_typed_models():
    user = AccessUser.from_dict({"id": 1, "right": "write", "email": "a@b.c"})
    assert user.right == "write"
    cat = Category.from_dict({"id": 2, "name": "Urgent", "color": "#f00"})
    assert cat.name == "Urgent"
    imp = ExternalImport.from_dict({"id": 9, "status": "done", "application": "dropbox"})
    assert imp.application == "dropbox"
