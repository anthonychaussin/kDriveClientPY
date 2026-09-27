from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest
import responses

from kdrive_client import AccessUser, Category, Comment, Invitation, KDriveClient
from kdrive_client.smart import AWAKE_THROTTLE_SECONDS, _trash_match_rank


BASE = "https://api.infomaniak.com"
DRIVE_ID = "12345"
TOKEN = "test-token"


@pytest.fixture
def client() -> KDriveClient:
    return KDriveClient(TOKEN, DRIVE_ID, parallelism=2, max_retries=0, timeout=5.0)


def _page(items, has_more=False, cursor=None):
    return {
        "result": "success",
        "data": items,
        "has_more": has_more,
        "cursor": cursor,
    }


@responses.activate
def test_resolve_and_ensure_path(client: KDriveClient) -> None:
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/1/name",
        json={"result": "success", "data": {"id": 10, "name": "a", "type": "dir"}},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/10/name",
        json={"result": "error", "error": {"code": "not_found", "description": "missing"}},
        status=404,
    )
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/10/files",
        json=_page([]),
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/3/drive/{DRIVE_ID}/files/10/directory",
        json={"result": "success", "data": {"id": 20, "name": "b", "type": "dir"}},
        status=200,
    )

    leaf = client.ensure_path("a/b")
    assert leaf.id == 20
    assert leaf.name == "b"

    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/1/name",
        json={"result": "success", "data": {"id": 10, "name": "a", "type": "dir"}},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/10/name",
        json={"result": "success", "data": {"id": 20, "name": "b", "type": "dir"}},
        status=200,
    )
    resolved = client.resolve_path("/a/b")
    assert resolved.id == 20


@responses.activate
def test_upload_from_path_and_tree(client: KDriveClient, tmp_path: Path) -> None:
    local = tmp_path / "tree"
    local.mkdir()
    nested = local / "sub"
    nested.mkdir()
    (nested / "hello.txt").write_bytes(b"hello")

    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/1",
        json={"result": "success", "data": {"id": 1, "name": "root", "type": "dir"}},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/1/name",
        json={"result": "success", "data": {"id": 50, "name": "sub", "type": "dir"}},
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/3/drive/{DRIVE_ID}/upload",
        json={"result": "success", "data": {"id": 99, "name": "hello.txt", "type": "file"}},
        status=200,
    )

    uploaded = client.upload_tree(local, remote_dir_id=1)
    assert len(uploaded) == 1
    assert uploaded[0].id == 99


@responses.activate
def test_download_folder(client: KDriveClient, tmp_path: Path) -> None:
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
        f"{BASE}/3/drive/{DRIVE_ID}/files/7/files",
        json=_page(
            [
                {"id": 8, "name": "f.txt", "type": "file"},
                {"id": 9, "name": "sub", "type": "dir"},
            ]
        ),
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/files/8/download",
        body=b"abc",
        status=200,
        content_type="application/octet-stream",
    )
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/files/9/files",
        json=_page([]),
        status=200,
    )

    out = tmp_path / "out"
    client.download_folder(7, out)
    assert (out / "f.txt").read_bytes() == b"abc"
    assert (out / "sub").is_dir()


@responses.activate
def test_bootstrap_rebind(client: KDriveClient) -> None:
    responses.add(
        responses.GET,
        f"{BASE}/2/drive",
        json={
            "result": "success",
            "data": [
                {"id": 111, "name": "A"},
                {"id": 222, "name": "B"},
            ],
        },
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BASE}/3/drive/222/wake",
        json={"result": "success", "data": True},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/222",
        json={"result": "success", "data": {"id": 222, "name": "B"}},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/222/files/1/files",
        json=_page([]),
        status=200,
    )

    drive, root = client.bootstrap(account_id=9, preferred_drive_id=222)
    assert client.drive_id == "222"
    assert drive.id == 222
    assert len(root) == 0


def test_awake_throttle(client: KDriveClient) -> None:
    with mock.patch.object(client, "wake") as wake, mock.patch.object(
        client, "get_drive", return_value=mock.Mock()
    ):
        client.ensure_drive_awake(force=True)
        client.ensure_drive_awake()
        assert wake.call_count == 1
        client._last_awake_at = 0.0
        client.ensure_drive_awake(throttle_seconds=AWAKE_THROTTLE_SECONDS)
        assert wake.call_count == 2


def test_trash_match_rank():
    item = mock.Mock()
    item.name = "report.pdf"
    item.path = "/trash/old/report.pdf"
    assert _trash_match_rank(item, "report.pdf", exact=True) == 3
    item.name = "other.pdf"
    assert _trash_match_rank(item, "report.pdf", exact=True) == 2
    assert _trash_match_rank(item, "report", exact=False) >= 1


@responses.activate
def test_search_all_and_typed_lists(client: KDriveClient) -> None:
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
        f"{BASE}/3/drive/{DRIVE_ID}/files/search",
        json=_page([{"id": 1, "name": "x.txt", "type": "file"}]),
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/categories",
        json={"result": "success", "data": [{"id": 1, "name": "tag", "color": "#fff"}]},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/files/5/comments",
        json={"result": "success", "data": [{"id": 2, "body": "hi", "user": {"id": 9}}]},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/3/drive/{DRIVE_ID}/users",
        json={"result": "success", "data": [{"id": 3, "email": "a@b.c"}]},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/invitations",
        json={"result": "success", "data": [{"id": 4, "email": "i@b.c", "right": "read"}]},
        status=200,
    )

    assert len(client.search_all(query="x")) == 1
    assert isinstance(client.list_all_categories()[0], Category)
    assert isinstance(client.list_all_comments(5)[0], Comment)
    assert isinstance(client.list_all_users()[0], AccessUser)
    assert isinstance(client.list_all_invitations()[0], Invitation)


@responses.activate
def test_copy_between_drives_wait(client: KDriveClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/2/drive/{DRIVE_ID}/files/1/copy-to-drive",
        json={"result": "success", "data": {"id": 77, "status": "running"}},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/imports/77",
        json={"result": "success", "data": {"id": 77, "status": "done"}},
        status=200,
    )
    result = client.copy_between_drives(
        1,
        destination_drive_id=999,
        destination_directory_id=1,
        wait=True,
        poll_interval=0.01,
    )
    assert result["status"] == "done"


@responses.activate
def test_wait_for_archive(client: KDriveClient) -> None:
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/files/archives/arch-1",
        json={"result": "success", "data": {"status": "pending"}},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE}/2/drive/{DRIVE_ID}/files/archives/arch-1",
        json={"result": "success", "data": {"status": "ready"}},
        status=200,
    )
    status = client.wait_for_archive("arch-1", timeout=5.0, poll_interval=0.01)
    assert status["status"] == "ready"
