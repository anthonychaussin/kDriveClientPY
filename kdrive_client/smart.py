from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

from .enums import ConflictMode
from .models import (
    AccessUser,
    Category,
    Comment,
    DriveDirectory,
    DriveEntry,
    DriveFile,
    DriveInfo,
    Invitation,
    KDriveApiException,
    KDriveFile,
    PaginatedList,
    iter_paginated,
)

JsonDict = Dict[str, Any]

AWAKE_THROTTLE_SECONDS = 120.0


def _split_remote_path(path: str) -> List[str]:
    normalized = path.replace("\\", "/").strip("/")
    return [part for part in normalized.split("/") if part]


def _item_path(item: Any) -> str:
    path = getattr(item, "path", None)
    if path:
        return str(path)
    raw = getattr(item, "raw", None)
    if isinstance(raw, dict):
        return str(raw.get("path") or raw.get("full_path") or "")
    if isinstance(item, dict):
        return str(item.get("path") or item.get("full_path") or "")
    return ""


def _trash_match_rank(item: Any, needle: str, *, exact: bool) -> int:
    """Higher is better: exact name (3) > path suffix (2) > contains (1)."""
    name = getattr(item, "name", None) or (item.get("name") if isinstance(item, dict) else "") or ""
    path = _item_path(item)
    if exact:
        if name == needle:
            return 3
        if path.endswith("/" + needle) or path.endswith(needle):
            return 2
        return 0
    lower_needle = needle.lower()
    lower_name = name.lower()
    lower_path = path.lower()
    if lower_name == lower_needle:
        return 3
    if lower_path.endswith("/" + lower_needle) or lower_path.endswith(lower_needle):
        return 2
    if lower_needle in lower_name or lower_needle in lower_path:
        return 1
    return 0


def _coerce_list(result: Any, *keys: str) -> List[Any]:
    if isinstance(result, list):
        return result
    if isinstance(result, PaginatedList):
        return list(result.items)
    if isinstance(result, dict):
        for key in keys:
            value = result.get(key)
            if isinstance(value, list):
                return value
        data = result.get("data")
        if isinstance(data, list):
            return data
    if result is None:
        return []
    return [result]


def _map_typed(items: List[Any], factory: Callable[[Dict[str, Any]], Any]) -> List[Any]:
    out: List[Any] = []
    for item in items:
        if isinstance(item, dict):
            try:
                out.append(factory(item))
            except (KeyError, TypeError, ValueError):
                out.append(item)
        else:
            out.append(item)
    return out


class SmartMixin:
    """Higher-level helpers composing drive/file mixins."""

    _last_awake_at: float = 0.0

    def rebind_drive_id(self, drive_id: Union[str, int]) -> None:
        """Switch the client to another drive (updates URL base for subsequent calls)."""
        self.drive_id = str(drive_id)

    def ensure_drive_awake(
        self,
        *,
        with_: Optional[Any] = None,
        force: bool = False,
        throttle_seconds: float = AWAKE_THROTTLE_SECONDS,
    ) -> DriveInfo:
        now = time.monotonic()
        last = getattr(self, "_last_awake_at", 0.0)
        if force or (now - last) >= max(0.0, throttle_seconds):
            try:
                self.wake()
            except KDriveApiException:
                pass
            self._last_awake_at = now
        return self.get_drive(with_=with_)

    def _maybe_wake(self) -> None:
        try:
            self.ensure_drive_awake()
        except Exception:
            pass

    def bootstrap(
        self,
        *,
        root_id: Union[str, int] = 1,
        with_: Optional[Any] = None,
        account_id: Optional[Union[str, int]] = None,
        preferred_drive_id: Optional[Union[str, int]] = None,
    ) -> Tuple[DriveInfo, PaginatedList[DriveEntry]]:
        if account_id is not None:
            drives = self.list_drives(account_id)
            selected: Optional[DriveInfo] = None
            if preferred_drive_id is not None:
                preferred = str(preferred_drive_id)
                selected = next((d for d in drives if str(d.id) == preferred), None)
            if selected is None and drives:
                selected = drives[0]
            if selected is None:
                raise KDriveApiException("not_found", f"No drives found for account {account_id}")
            self.rebind_drive_id(selected.id)
        drive = self.ensure_drive_awake(with_=with_)
        root = self.list_files(root_id, with_=with_)
        return drive, root

    # --- Path helpers -----------------------------------------------------

    def resolve_path(
        self,
        path: str,
        *,
        parent_id: Union[str, int] = 1,
        with_: Optional[Any] = None,
    ) -> DriveDirectory:
        """Resolve a remote folder path like ``/a/b/c`` to a directory entry."""
        segments = _split_remote_path(path)
        if not segments:
            entry = self.get_file(parent_id, with_=with_)
            if not isinstance(entry, DriveDirectory):
                raise KDriveApiException("invalid_path", f"Parent {parent_id} is not a directory")
            return entry

        current_id: Union[str, int] = parent_id
        current: Optional[DriveDirectory] = None
        for segment in segments:
            try:
                found = self.find_by_name(current_id, segment, with_=with_)
            except KDriveApiException:
                found = None
                for child in self.iter_files(current_id, with_=with_):
                    if isinstance(child, DriveDirectory) and child.name == segment:
                        found = child
                        break
            if found is None:
                raise KDriveApiException("not_found", f"Path segment not found: {segment!r} in {path!r}")
            if not isinstance(found, DriveDirectory):
                raise KDriveApiException("invalid_path", f"Path segment is not a directory: {segment!r}")
            current = found
            current_id = found.id
        assert current is not None
        return current

    def ensure_path(
        self,
        path: str,
        *,
        parent_id: Union[str, int] = 1,
        **kwargs: Any,
    ) -> DriveDirectory:
        """Create missing folders along ``path`` and return the leaf directory."""
        segments = _split_remote_path(path)
        if not segments:
            entry = self.get_file(parent_id)
            if isinstance(entry, DriveDirectory):
                return entry
            raise KDriveApiException("invalid_path", f"Parent {parent_id} is not a directory")

        current_id: Union[str, int] = parent_id
        current: Optional[DriveDirectory] = None
        for segment in segments:
            current = self.get_or_create_folder(current_id, segment, **kwargs)
            current_id = current.id
        assert current is not None
        return current

    def get_or_create_folder(
        self,
        parent_id: Union[str, int],
        name: str,
        **kwargs: Any,
    ) -> DriveDirectory:
        try:
            entry = self.find_by_name(parent_id, name)
            if isinstance(entry, DriveDirectory):
                return entry
        except KDriveApiException:
            pass

        for child in self.iter_files(parent_id):
            if isinstance(child, DriveDirectory) and child.name == name:
                return child

        try:
            return self.create_directory(parent_id, name, **kwargs)
        except KDriveApiException as exc:
            if "already" not in str(exc).lower() and "exists" not in str(exc).lower():
                raise
            for child in self.iter_files(parent_id):
                if isinstance(child, DriveDirectory) and child.name == name:
                    return child
            raise

    # --- Local ↔ cloud tree I/O -------------------------------------------

    def upload_from_path(
        self,
        local_path: Union[str, Path],
        *,
        remote_dir_id: Optional[Union[str, int]] = None,
        remote_path: Optional[str] = None,
        preserve_timestamps: bool = True,
        conflict: Optional[ConflictMode] = None,
        **upload_kwargs: Any,
    ) -> DriveFile:
        """Upload a local file; create ``remote_path`` folders when given."""
        path = Path(local_path)
        if not path.is_file():
            raise FileNotFoundError(f"Not a file: {path}")
        if remote_dir_id is None and remote_path is None:
            raise ValueError("Provide remote_dir_id or remote_path")
        directory_id: Union[str, int]
        if remote_path is not None:
            parent = int(remote_dir_id) if remote_dir_id is not None else 1
            directory_id = self.ensure_path(remote_path, parent_id=parent).id
        else:
            assert remote_dir_id is not None
            directory_id = remote_dir_id

        created_at = last_modified_at = None
        if preserve_timestamps:
            stat = path.stat()
            created_at = int(getattr(stat, "st_ctime", stat.st_mtime))
            last_modified_at = int(stat.st_mtime)

        with path.open("rb") as handle:
            kfile = KDriveFile(
                name=path.name,
                directory_id=int(directory_id),
                content=handle,
                total_size=path.stat().st_size,
                created_at=created_at,
                last_modified_at=last_modified_at,
            )
            return self.upload(kfile, conflict=conflict, **upload_kwargs)

    def download_folder(
        self,
        directory: Union[str, int],
        local_dir: Union[str, Path],
        *,
        recursive: bool = True,
        parent_id: Union[str, int] = 1,
    ) -> Path:
        """Download a remote folder tree into ``local_dir`` (one-way)."""
        dest = Path(local_dir)
        dest.mkdir(parents=True, exist_ok=True)

        if isinstance(directory, int) or (isinstance(directory, str) and directory.isdigit()):
            directory_id: Union[str, int] = int(directory) if isinstance(directory, str) else directory
        else:
            directory_id = self.resolve_path(str(directory), parent_id=parent_id).id

        self._maybe_wake()
        for entry in self.enumerate_files(directory_id):
            if isinstance(entry, DriveDirectory):
                child_dir = dest / entry.name
                if recursive:
                    self.download_folder(entry.id, child_dir, recursive=True)
                else:
                    child_dir.mkdir(parents=True, exist_ok=True)
            elif isinstance(entry, DriveFile):
                self.download_to_path(entry.id, dest / entry.name)
        return dest

    def upload_tree(
        self,
        local_dir: Union[str, Path],
        *,
        remote_dir_id: Optional[Union[str, int]] = None,
        remote_path: Optional[str] = None,
        conflict: Optional[ConflictMode] = ConflictMode.RENAME,
        preserve_timestamps: bool = True,
        **upload_kwargs: Any,
    ) -> List[DriveFile]:
        """Mirror a local directory tree to the drive (one-way upload)."""
        root = Path(local_dir)
        if not root.is_dir():
            raise NotADirectoryError(f"Not a directory: {root}")
        if remote_dir_id is None and remote_path is None:
            raise ValueError("Provide remote_dir_id or remote_path")

        if remote_path is not None:
            parent = int(remote_dir_id) if remote_dir_id is not None else 1
            base = self.ensure_path(remote_path, parent_id=parent)
        else:
            assert remote_dir_id is not None
            entry = self.get_file(remote_dir_id)
            if not isinstance(entry, DriveDirectory):
                raise KDriveApiException("invalid_path", f"{remote_dir_id} is not a directory")
            base = entry

        uploaded: List[DriveFile] = []
        for dirpath, _dirnames, filenames in os.walk(root):
            rel = Path(dirpath).relative_to(root)
            if str(rel) == ".":
                target_id = base.id
            else:
                target_id = self.ensure_path(rel.as_posix(), parent_id=base.id).id
            for name in filenames:
                local_file = Path(dirpath) / name
                uploaded.append(
                    self.upload_from_path(
                        local_file,
                        remote_dir_id=target_id,
                        preserve_timestamps=preserve_timestamps,
                        conflict=conflict,
                        **upload_kwargs,
                    )
                )
        return uploaded

    # --- Enumerate / list_all ---------------------------------------------

    def enumerate_files(
        self,
        directory_id: Union[str, int] = 1,
        **kwargs: Any,
    ) -> Iterator[DriveEntry]:
        self._maybe_wake()
        return iter_paginated(self.list_files, directory_id, **kwargs)

    def enumerate_search(self, **kwargs: Any) -> Iterator[DriveEntry]:
        self._maybe_wake()
        return iter_paginated(self.search, **kwargs)

    def enumerate_favorites(self, **kwargs: Any) -> Iterator[DriveEntry]:
        self._maybe_wake()
        return iter_paginated(self.list_favorites, **kwargs)

    def enumerate_trash(self, **kwargs: Any) -> Iterator[DriveEntry]:
        self._maybe_wake()
        return iter_paginated(self.list_trash, **kwargs)

    def enumerate_search_trash(self, **kwargs: Any) -> Iterator[DriveEntry]:
        self._maybe_wake()
        return iter_paginated(self.search_trash, **kwargs)

    def enumerate_dropboxes(self, **kwargs: Any) -> Iterator[DriveEntry]:
        return iter_paginated(self.list_dropboxes, **kwargs)

    def enumerate_links(self, **kwargs: Any) -> Iterator[DriveEntry]:
        return iter_paginated(self.list_links, **kwargs)

    def enumerate_categories(self, **kwargs: Any) -> Iterator[Any]:
        result = self.list_categories(**kwargs)
        yield from _coerce_list(result, "categories", "data")

    def enumerate_comments(self, file_id: Union[str, int], **kwargs: Any) -> Iterator[Any]:
        result = self.list_comments(file_id, **kwargs)
        yield from _coerce_list(result, "comments", "data")

    def enumerate_users(self, **kwargs: Any) -> Iterator[Any]:
        result = self.list_users(**kwargs)
        yield from _coerce_list(result, "users", "data")

    def enumerate_invitations(self, **kwargs: Any) -> Iterator[Any]:
        result = self.list_invitations(**kwargs)
        yield from _coerce_list(result, "invitations", "data")

    def enumerate_recents(self, **kwargs: Any) -> Iterator[DriveEntry]:
        self._maybe_wake()
        return iter_paginated(self.list_recents, **kwargs)

    def enumerate_my_shared(self, **kwargs: Any) -> Iterator[DriveEntry]:
        return iter_paginated(self.list_my_shared, **kwargs)

    def enumerate_shared_with_me(self, **kwargs: Any) -> Iterator[DriveEntry]:
        return iter_paginated(self.list_shared_with_me, **kwargs)

    def enumerate_trash_children(
        self,
        dir_id: Union[str, int],
        **kwargs: Any,
    ) -> Iterator[DriveEntry]:
        return iter_paginated(self.list_trash_children, dir_id, **kwargs)

    def list_all_favorites(self, **kwargs: Any) -> List[DriveEntry]:
        return list(self.enumerate_favorites(**kwargs))

    def list_all_trash(self, **kwargs: Any) -> List[DriveEntry]:
        return list(self.enumerate_trash(**kwargs))

    def search_trash_all(self, **kwargs: Any) -> List[DriveEntry]:
        return list(self.enumerate_search_trash(**kwargs))

    def search_all(self, **kwargs: Any) -> List[DriveEntry]:
        """Materialize all search pages (alias of ``list(enumerate_search(...))``)."""
        return list(self.enumerate_search(**kwargs))

    def list_all_dropboxes(self, **kwargs: Any) -> List[DriveEntry]:
        return list(self.enumerate_dropboxes(**kwargs))

    def list_all_links(self, **kwargs: Any) -> List[DriveEntry]:
        return list(self.enumerate_links(**kwargs))

    def list_all_categories(self, **kwargs: Any) -> List[Any]:
        return _map_typed(list(self.enumerate_categories(**kwargs)), Category.from_dict)

    def list_all_comments(self, file_id: Union[str, int], **kwargs: Any) -> List[Any]:
        return _map_typed(list(self.enumerate_comments(file_id, **kwargs)), Comment.from_dict)

    def list_all_users(self, **kwargs: Any) -> List[Any]:
        return _map_typed(list(self.enumerate_users(**kwargs)), AccessUser.from_dict)

    def list_all_invitations(self, **kwargs: Any) -> List[Any]:
        return _map_typed(list(self.enumerate_invitations(**kwargs)), Invitation.from_dict)

    def list_trash_children_all(self, dir_id: Union[str, int], **kwargs: Any) -> List[DriveEntry]:
        return list(self.enumerate_trash_children(dir_id, **kwargs))

    def list_versions_all(self, file_id: Union[str, int]) -> List[Dict[str, Any]]:
        versions = self.list_versions(file_id)
        items = _coerce_list(versions, "versions", "data", "items")
        return [item for item in items if isinstance(item, dict)]

    def list_file_activities_all(
        self,
        file_id: Optional[Union[str, int]] = None,
        **kwargs: Any,
    ) -> List[Any]:
        result = self.list_activities(file_id, **kwargs)
        return _coerce_list(result, "activities", "data", "items")

    def list_drive_activities_all(self, **kwargs: Any) -> List[Any]:
        result = self.list_drive_activities(**kwargs)
        return _coerce_list(result, "activities", "data", "items")

    def find_trash_item(
        self,
        name: str,
        *,
        exact: bool = True,
        **kwargs: Any,
    ) -> Optional[DriveEntry]:
        best: Optional[DriveEntry] = None
        best_rank = 0
        for item in self.enumerate_trash(**kwargs):
            rank = _trash_match_rank(item, name, exact=exact)
            if rank > best_rank:
                best = item
                best_rank = rank
                if rank >= 3:
                    return item
        return best if best_rank > 0 else None

    def find_latest_version(self, file_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        items = self.list_versions_all(file_id)
        if not items:
            return None

        def _key(item: Dict[str, Any]) -> Any:
            return (
                item.get("created_at")
                or item.get("last_modified_at")
                or item.get("updated_at")
                or item.get("id")
                or 0
            )

        return max(items, key=_key)

    def restore_latest_version(self, file_id: Union[str, int]) -> Any:
        latest = self.find_latest_version(file_id)
        if latest is None:
            raise KDriveApiException("not_found", "No versions available for this file")
        version_id = latest.get("id") or latest.get("version_id")
        if version_id is None:
            raise KDriveApiException("unexpected_payload", "Version payload missing id")
        return self.restore_version(file_id, version_id)

    def restore_latest_version_to(
        self,
        file_id: Union[str, int],
        dest_id: Union[str, int],
    ) -> Any:
        latest = self.find_latest_version(file_id)
        if latest is None:
            raise KDriveApiException("not_found", "No versions available for this file")
        version_id = latest.get("id") or latest.get("version_id")
        if version_id is None:
            raise KDriveApiException("unexpected_payload", "Version payload missing id")
        return self.restore_version_to(file_id, version_id, dest_id)

    def wait_for_async_result(
        self,
        poll: Optional[Callable[[], Any]] = None,
        *,
        file_id: Optional[Union[str, int]] = None,
        timeout: float = 120.0,
        poll_interval: float = 1.0,
        locked_statuses: Optional[set] = None,
        is_done: Optional[Callable[[Any], bool]] = None,
        with_: Optional[Any] = None,
        on_poll: Optional[Callable[[Any], None]] = None,
    ) -> Any:
        """Poll until complete.

        - If ``poll`` is provided, call it until ``is_done(result)`` (default: truthy non-locked).
        - Else poll ``get_file(file_id)`` until status leaves locked set.
        """
        locked = locked_statuses or {"locked", "uploading", "processing", "pending", "running"}
        deadline = time.monotonic() + max(0.0, timeout)
        last: Any = None

        def _default_done(value: Any) -> bool:
            if value is None:
                return False
            status = getattr(value, "status", None)
            if status is None and isinstance(value, dict):
                status = value.get("status") or value.get("state")
            if status is None:
                return True
            return str(status).lower() not in locked

        done_fn = is_done or _default_done

        while True:
            if poll is not None:
                last = poll()
            elif file_id is not None:
                last = self.get_file(file_id, with_=with_)
            else:
                raise ValueError("Provide poll= callable or file_id=")
            if on_poll is not None:
                on_poll(last)
            if done_fn(last):
                return last
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for async result (last={last!r})")
            time.sleep(max(0.05, poll_interval))

    def wait_for_import_complete(
        self,
        import_id: Union[str, int],
        *,
        timeout: float = 600.0,
        poll_interval: float = 2.0,
        done_statuses: Optional[set] = None,
    ) -> Dict[str, Any]:
        done = done_statuses or {
            "done",
            "success",
            "completed",
            "finished",
            "error",
            "failed",
            "canceled",
            "cancelled",
        }

        def _poll() -> Dict[str, Any]:
            return self.get_import(import_id)

        def _is_done(value: Any) -> bool:
            if not isinstance(value, dict):
                return False
            status = str(value.get("status") or value.get("state") or "").lower()
            return status in done

        result = self.wait_for_async_result(
            _poll,
            timeout=timeout,
            poll_interval=poll_interval,
            is_done=_is_done,
        )
        return result if isinstance(result, dict) else {"data": result}

    def wait_for_archive(
        self,
        uuid: str,
        *,
        timeout: float = 300.0,
        poll_interval: float = 1.0,
    ) -> Dict[str, Any]:
        """Poll archive status until ready (or downloadable)."""
        ready = {"ready", "done", "success", "completed", ""}
        failed = {"error", "failed"}

        def _poll() -> Dict[str, Any]:
            try:
                return self.get_archive_status(str(uuid))
            except Exception:
                return {"status": "pending"}

        def _is_done(value: Any) -> bool:
            if not isinstance(value, dict):
                return False
            state = str(value.get("status") or value.get("state") or "").lower()
            if state in failed:
                raise RuntimeError(f"Archive {uuid} failed: {value}")
            return state in ready

        result = self.wait_for_async_result(
            _poll,
            timeout=timeout,
            poll_interval=poll_interval,
            is_done=_is_done,
        )
        return result if isinstance(result, dict) else {"data": result}

    def copy_between_drives(
        self,
        file_id: Union[str, int],
        *,
        destination_drive_id: Union[str, int],
        destination_directory_id: Union[str, int],
        source_drive_id: Optional[Union[str, int]] = None,
        wait: bool = False,
        timeout: float = 600.0,
        poll_interval: float = 2.0,
        **extra: Any,
    ) -> Any:
        body = {
            "destination_drive_id": destination_drive_id,
            "destination_directory_id": destination_directory_id,
            **extra,
        }
        if source_drive_id is not None:
            body["source_drive_id"] = source_drive_id
        result = self.copy_to_drive(file_id, body)
        if not wait:
            return result
        import_id = None
        if isinstance(result, dict):
            nested = result.get("data")
            import_id = result.get("id") or result.get("import_id")
            if import_id is None and isinstance(nested, dict):
                import_id = nested.get("id") or nested.get("import_id")
        if import_id is None:
            return result
        return self.wait_for_import_complete(
            import_id,
            timeout=timeout,
            poll_interval=poll_interval,
        )
