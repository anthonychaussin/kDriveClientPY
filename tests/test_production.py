from __future__ import annotations

import io
import os

import pytest
import responses

from kdrive_client import (
    ActivityReport,
    AsyncKDriveClient,
    Comment,
    Invitation,
    KDriveClient,
    KDriveFile,
    suggest_direct_threshold,
)


BASE = "https://api.infomaniak.com"
DRIVE_ID = "12345"
TOKEN = "test-token"


@pytest.fixture
def client() -> KDriveClient:
    return KDriveClient(TOKEN, DRIVE_ID, parallelism=2, max_retries=0, timeout=5.0)


def test_suggest_direct_threshold():
    assert suggest_direct_threshold(0) == 100 * 1024 * 1024
    assert 10 * 1024 * 1024 <= suggest_direct_threshold(1_000_000) <= 100 * 1024 * 1024


@responses.activate
def test_upload_timing_params(client: KDriveClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/3/drive/{DRIVE_ID}/upload",
        json={"result": "success", "data": {"id": 1, "name": "a.txt", "type": "file"}},
        status=200,
    )
    f = KDriveFile(
        name="a.txt",
        directory_id=1,
        content=io.BytesIO(b"hi"),
        created_at=1700000000,
        last_modified_at=1700000001,
    )
    client.upload_direct(f)
    assert "created_at=1700000000" in responses.calls[0].request.url
    assert "last_modified_at=1700000001" in responses.calls[0].request.url


@responses.activate
def test_download_progress(client: KDriveClient) -> None:
    seen = []
    client.download_progress_callback = lambda p: seen.append(p)
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/files/9/download",
        body=b"abcdefgh",
        status=200,
        headers={"Content-Length": "8"},
        content_type="application/octet-stream",
    )
    data = b"".join(client.download_iter(9, chunk_size=4, total_size=8))
    assert data == b"abcdefgh"
    assert seen
    assert seen[-1] == 100.0


def test_new_dataclasses():
    c = Comment.from_dict({"id": 1, "body": "hi", "user": {"id": 9}})
    assert c.user_id == 9
    inv = Invitation.from_dict({"id": 2, "email": "a@b.c", "right": "write"})
    assert inv.email == "a@b.c"
    rep = ActivityReport.from_dict({"id": 3, "name": "weekly", "status": "ready"})
    assert rep.name == "weekly"


@pytest.mark.asyncio
async def test_async_client_list_files():
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            f"{BASE}/3/drive/{DRIVE_ID}/files/1/files",
            json={"result": "success", "data": [], "has_more": False},
            status=200,
        )
        async with AsyncKDriveClient(TOKEN, DRIVE_ID) as client:
            page = await client.list_files(1)
            assert len(page) == 0


@pytest.mark.integration
def test_live_get_drive():
    token = os.environ.get("KDRIVE_TOKEN")
    drive_id = os.environ.get("KDRIVE_DRIVE_ID")
    if not token or not drive_id:
        pytest.skip("KDRIVE_TOKEN / KDRIVE_DRIVE_ID not set")
    with KDriveClient(token, drive_id) as client:
        drive = client.get_drive()
        assert drive.id
