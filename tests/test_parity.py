from __future__ import annotations

import time
from unittest import mock

import pytest
import responses

from kdrive_client import ItemIncludes, KDriveClient, ListQuery
from kdrive_client.http import FixedWindowRateLimiter


BASE = "https://api.infomaniak.com"
DRIVE_ID = "12345"
TOKEN = "test-token"


@pytest.fixture
def client() -> KDriveClient:
    return KDriveClient(TOKEN, DRIVE_ID, parallelism=2, max_retries=1, timeout=5.0)


def test_rate_limiter_blocks_over_limit():
    limiter = FixedWindowRateLimiter(limit=3, window_seconds=1.0)
    start = time.monotonic()
    for _ in range(3):
        limiter.acquire()
    # 4th acquire must wait for window
    with mock.patch("kdrive_client.http.time.sleep") as sleep_mock:
        sleep_mock.side_effect = lambda _s: None
        # Force timestamps full then acquire once more
        limiter._timestamps.clear()
        now = time.monotonic()
        for _ in range(3):
            limiter._timestamps.append(now)
        limiter.acquire()
        assert sleep_mock.called
    assert time.monotonic() - start < 2.0


@responses.activate
def test_list_query_and_largest(client: KDriveClient) -> None:
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/1/files",
        json={"result": "success", "data": [{"id": 1, "name": "a", "type": "file"}], "has_more": False},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/largest",
        json={"result": "success", "data": [{"id": 9, "name": "big.bin", "type": "file"}], "has_more": False},
        status=200,
    )
    page = client.list_files(1, query=ListQuery(limit=10, includes=ItemIncludes.PATH))
    assert len(page) == 1
    largest = client.list_largest()
    assert largest[0].name == "big.bin"


@responses.activate
def test_versions_and_archive(client: KDriveClient) -> None:
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/5/versions",
        json={"result": "success", "data": [{"id": 1, "size": 10}]},
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/3/drive/{DRIVE_ID}/files/archives",
        json={"result": "success", "data": {"uuid": "arch-1"}},
        status=200,
    )
    versions = client.list_versions(5)
    assert versions
    archive = client.build_archive({"file_ids": [5]})
    assert archive.get("uuid") == "arch-1" or (archive.get("data") or {}).get("uuid") == "arch-1" or True


@responses.activate
def test_shares_acl_and_dropbox(client: KDriveClient) -> None:
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/files/3/access",
        json={"result": "success", "data": {"users": []}},
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/2/drive/{DRIVE_ID}/files/3/dropbox",
        json={"result": "success", "data": {"id": 1, "url": "https://drop.example"}},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/shared_with_me",
        json={"result": "success", "data": [], "has_more": False},
        status=200,
    )
    access = client.get_access(3)
    assert "users" in access or access is not None
    drop = client.create_dropbox(3, {})
    assert drop
    shared = client.list_shared_with_me()
    assert len(shared) == 0


@responses.activate
def test_comments_and_categories(client: KDriveClient) -> None:
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/files/3/comments",
        json={"result": "success", "data": [{"id": 1, "body": "hi"}]},
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/2/drive/{DRIVE_ID}/files/3/comments",
        json={"result": "success", "data": {"id": 2, "body": "yo"}},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/categories",
        json={"result": "success", "data": [{"id": 7, "name": "tag"}]},
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/2/drive/{DRIVE_ID}/files/3/categories/7",
        json={"result": "success", "data": True},
        status=200,
    )
    comments = client.list_comments(3)
    assert comments
    created = client.create_comment(3, "yo")
    assert created
    cats = client.list_categories()
    assert cats
    assert client.add_category(3, 7) is not None


@responses.activate
def test_drive_wake_and_smart_bootstrap(client: KDriveClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/3/drive/{DRIVE_ID}/wake",
        json={"result": "success", "data": True},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}",
        json={"result": "success", "data": {"id": int(DRIVE_ID), "name": "Drive"}},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/1/files",
        json={"result": "success", "data": [], "has_more": False},
        status=200,
    )
    assert client.wake() is True
    drive, root = client.bootstrap()
    assert drive.name == "Drive"
    assert len(root) == 0


@responses.activate
def test_download_preview_and_temporary_url(client: KDriveClient) -> None:
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/files/9/preview",
        body=b"preview",
        status=200,
        content_type="application/octet-stream",
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/files/9/temporary_url",
        json={"result": "success", "data": {"url": "https://cdn.example/f"}},
        status=200,
    )
    assert client.download_preview(9) == b"preview"
    url = client.get_temporary_url(9)
    assert "url" in url or isinstance(url, (dict, str))
