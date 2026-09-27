from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Iterator, List, Optional, TypeVar, Union


T = TypeVar("T")


def _get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    return data.get(key, default)


@dataclass
class CancelAction:
    cancel_id: str
    valid_until: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CancelAction":
        return cls(
            cancel_id=str(data["cancel_id"]),
            valid_until=_get(data, "valid_until"),
        )


@dataclass
class UploadSession:
    token: str
    upload_url: str
    directory_id: Optional[int] = None
    directory_path: Optional[str] = None
    file_name: Optional[str] = None
    file_id: Optional[int] = None
    message: Optional[str] = None
    result: Optional[str] = None
    file: Optional["DriveEntry"] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UploadSession":
        raw_file = data.get("file")
        return cls(
            token=str(data["token"]),
            upload_url=str(data["upload_url"]),
            directory_id=_get(data, "directory_id"),
            directory_path=_get(data, "directory_path"),
            file_name=_get(data, "file_name"),
            file_id=_get(data, "file_id"),
            message=_get(data, "message"),
            result=_get(data, "result"),
            file=parse_drive_entry(raw_file) if isinstance(raw_file, dict) else None,
        )


@dataclass
class DriveInfo:
    id: int
    name: str
    size: Optional[int] = None
    used_size: Optional[int] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    in_maintenance: Optional[bool] = None
    maintenance_at: Optional[int] = None
    version: Optional[str] = None
    users_count: Optional[int] = None
    users_quota: Optional[int] = None
    product_id: Optional[int] = None
    account_id: Optional[int] = None
    expired_at: Optional[int] = None
    is_locked: Optional[bool] = None
    is_demo: Optional[bool] = None
    role: Optional[str] = None
    account_admin: Optional[bool] = None
    is_in_app_subscription: Optional[bool] = None
    status: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DriveInfo":
        known = {
            "id",
            "name",
            "size",
            "used_size",
            "created_at",
            "updated_at",
            "in_maintenance",
            "maintenance_at",
            "version",
            "users_count",
            "users_quota",
            "product_id",
            "account_id",
            "expired_at",
            "is_locked",
            "is_demo",
            "role",
            "account_admin",
            "is_in_app_subscription",
            "status",
        }
        return cls(
            id=int(data["id"]),
            name=str(data["name"]),
            size=_get(data, "size"),
            used_size=_get(data, "used_size"),
            created_at=_get(data, "created_at"),
            updated_at=_get(data, "updated_at"),
            in_maintenance=_get(data, "in_maintenance"),
            maintenance_at=_get(data, "maintenance_at"),
            version=_get(data, "version"),
            users_count=_get(data, "users_count"),
            users_quota=_get(data, "users_quota"),
            product_id=_get(data, "product_id"),
            account_id=_get(data, "account_id"),
            expired_at=_get(data, "expired_at"),
            is_locked=_get(data, "is_locked"),
            is_demo=_get(data, "is_demo"),
            role=_get(data, "role"),
            account_admin=_get(data, "account_admin"),
            is_in_app_subscription=_get(data, "is_in_app_subscription"),
            status=_get(data, "status"),
            raw={k: v for k, v in data.items() if k not in known},
        )


@dataclass
class FileCount:
    count: int
    files: int = 0
    directories: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileCount":
        return cls(
            count=int(data.get("count") or 0),
            files=int(data.get("files") or 0),
            directories=int(data.get("directories") or 0),
        )


@dataclass
class AccessUser:
    id: int
    right: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessUser":
        known = {"id", "user_id", "right", "access", "name", "email", "display_name"}
        uid = data.get("id", data.get("user_id"))
        return cls(
            id=int(uid),
            right=_get(data, "right") or _get(data, "access"),
            name=_get(data, "name") or _get(data, "display_name"),
            email=_get(data, "email"),
            raw={k: v for k, v in data.items() if k not in known},
        )


@dataclass
class Category:
    id: int
    name: str
    color: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Category":
        known = {"id", "name", "color"}
        return cls(
            id=int(data["id"]),
            name=str(data["name"]),
            color=_get(data, "color"),
            raw={k: v for k, v in data.items() if k not in known},
        )


@dataclass
class ExternalImport:
    id: int
    status: Optional[str] = None
    application: Optional[str] = None
    path: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExternalImport":
        known = {"id", "status", "application", "path", "created_at", "updated_at"}
        return cls(
            id=int(data["id"]),
            status=_get(data, "status"),
            application=_get(data, "application"),
            path=_get(data, "path"),
            created_at=_get(data, "created_at"),
            updated_at=_get(data, "updated_at"),
            raw={k: v for k, v in data.items() if k not in known},
        )


@dataclass
class Comment:
    id: int
    body: Optional[str] = None
    user_id: Optional[int] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    is_resolved: Optional[bool] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Comment":
        known = {"id", "body", "user_id", "created_at", "updated_at", "is_resolved", "user"}
        user = data.get("user") if isinstance(data.get("user"), dict) else {}
        return cls(
            id=int(data["id"]),
            body=_get(data, "body"),
            user_id=_get(data, "user_id") or user.get("id"),
            created_at=_get(data, "created_at"),
            updated_at=_get(data, "updated_at"),
            is_resolved=_get(data, "is_resolved"),
            raw={k: v for k, v in data.items() if k not in known},
        )


@dataclass
class Invitation:
    id: int
    email: Optional[str] = None
    status: Optional[str] = None
    right: Optional[str] = None
    created_at: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Invitation":
        known = {"id", "email", "status", "right", "access", "created_at"}
        return cls(
            id=int(data["id"]),
            email=_get(data, "email"),
            status=_get(data, "status"),
            right=_get(data, "right") or _get(data, "access"),
            created_at=_get(data, "created_at"),
            raw={k: v for k, v in data.items() if k not in known},
        )


@dataclass
class ActivityReport:
    id: int
    name: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActivityReport":
        known = {"id", "name", "status", "created_at", "updated_at"}
        return cls(
            id=int(data["id"]),
            name=_get(data, "name"),
            status=_get(data, "status"),
            created_at=_get(data, "created_at"),
            updated_at=_get(data, "updated_at"),
            raw={k: v for k, v in data.items() if k not in known},
        )


@dataclass
class ShareLink:
    url: Optional[str] = None
    right: Optional[str] = None
    valid_until: Optional[int] = None
    can_download: Optional[bool] = None
    can_edit: Optional[bool] = None
    can_see_stats: Optional[bool] = None
    can_comment: Optional[bool] = None
    has_password: Optional[bool] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShareLink":
        known = {
            "url",
            "right",
            "valid_until",
            "can_download",
            "can_edit",
            "can_see_stats",
            "can_comment",
            "has_password",
        }
        return cls(
            url=_get(data, "url"),
            right=_get(data, "right"),
            valid_until=_get(data, "valid_until"),
            can_download=_get(data, "can_download"),
            can_edit=_get(data, "can_edit"),
            can_see_stats=_get(data, "can_see_stats"),
            can_comment=_get(data, "can_comment"),
            has_password=_get(data, "has_password"),
            raw={k: v for k, v in data.items() if k not in known},
        )


@dataclass
class DriveFile:
    id: int
    name: str
    type: str = "file"
    status: Optional[str] = None
    visibility: Optional[str] = None
    drive_id: Optional[int] = None
    depth: Optional[int] = None
    parent_id: Optional[int] = None
    size: Optional[int] = None
    mime_type: Optional[str] = None
    extension_type: Optional[str] = None
    scan_status: Optional[str] = None
    path: Optional[str] = None
    sorted_name: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[int] = None
    added_at: Optional[int] = None
    last_modified_at: Optional[int] = None
    last_modified_by: Optional[int] = None
    revised_at: Optional[int] = None
    updated_at: Optional[int] = None
    is_favorite: Optional[bool] = None
    etag: Optional[str] = None
    hash: Optional[str] = None
    sharelink: Optional[ShareLink] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DriveFile":
        known = {
            "id",
            "name",
            "type",
            "status",
            "visibility",
            "drive_id",
            "depth",
            "parent_id",
            "size",
            "mime_type",
            "extension_type",
            "scan_status",
            "path",
            "sorted_name",
            "created_by",
            "created_at",
            "added_at",
            "last_modified_at",
            "last_modified_by",
            "revised_at",
            "updated_at",
            "is_favorite",
            "etag",
            "hash",
            "sharelink",
        }
        raw_share = data.get("sharelink")
        return cls(
            id=int(data["id"]),
            name=str(data["name"]),
            type=str(_get(data, "type", "file")),
            status=_get(data, "status"),
            visibility=_get(data, "visibility"),
            drive_id=_get(data, "drive_id"),
            depth=_get(data, "depth"),
            parent_id=_get(data, "parent_id"),
            size=_get(data, "size"),
            mime_type=_get(data, "mime_type"),
            extension_type=_get(data, "extension_type"),
            scan_status=_get(data, "scan_status"),
            path=_get(data, "path"),
            sorted_name=_get(data, "sorted_name"),
            created_by=_get(data, "created_by"),
            created_at=_get(data, "created_at"),
            added_at=_get(data, "added_at"),
            last_modified_at=_get(data, "last_modified_at"),
            last_modified_by=_get(data, "last_modified_by"),
            revised_at=_get(data, "revised_at"),
            updated_at=_get(data, "updated_at"),
            is_favorite=_get(data, "is_favorite"),
            etag=_get(data, "etag"),
            hash=_get(data, "hash"),
            sharelink=ShareLink.from_dict(raw_share) if isinstance(raw_share, dict) else None,
            raw={k: v for k, v in data.items() if k not in known},
        )


@dataclass
class DriveDirectory:
    id: int
    name: str
    type: str = "dir"
    status: Optional[str] = None
    visibility: Optional[str] = None
    drive_id: Optional[int] = None
    depth: Optional[int] = None
    parent_id: Optional[int] = None
    path: Optional[str] = None
    sorted_name: Optional[str] = None
    color: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[int] = None
    added_at: Optional[int] = None
    last_modified_at: Optional[int] = None
    last_modified_by: Optional[int] = None
    revised_at: Optional[int] = None
    updated_at: Optional[int] = None
    is_favorite: Optional[bool] = None
    etag: Optional[str] = None
    sharelink: Optional[ShareLink] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DriveDirectory":
        known = {
            "id",
            "name",
            "type",
            "status",
            "visibility",
            "drive_id",
            "depth",
            "parent_id",
            "path",
            "sorted_name",
            "color",
            "created_by",
            "created_at",
            "added_at",
            "last_modified_at",
            "last_modified_by",
            "revised_at",
            "updated_at",
            "is_favorite",
            "etag",
            "sharelink",
        }
        raw_share = data.get("sharelink")
        return cls(
            id=int(data["id"]),
            name=str(data["name"]),
            type=str(_get(data, "type", "dir")),
            status=_get(data, "status"),
            visibility=_get(data, "visibility"),
            drive_id=_get(data, "drive_id"),
            depth=_get(data, "depth"),
            parent_id=_get(data, "parent_id"),
            path=_get(data, "path"),
            sorted_name=_get(data, "sorted_name"),
            color=_get(data, "color"),
            created_by=_get(data, "created_by"),
            created_at=_get(data, "created_at"),
            added_at=_get(data, "added_at"),
            last_modified_at=_get(data, "last_modified_at"),
            last_modified_by=_get(data, "last_modified_by"),
            revised_at=_get(data, "revised_at"),
            updated_at=_get(data, "updated_at"),
            is_favorite=_get(data, "is_favorite"),
            etag=_get(data, "etag"),
            sharelink=ShareLink.from_dict(raw_share) if isinstance(raw_share, dict) else None,
            raw={k: v for k, v in data.items() if k not in known},
        )


DriveEntry = Union[DriveFile, DriveDirectory]


def parse_drive_entry(data: Dict[str, Any]) -> DriveEntry:
    entry_type = data.get("type", "file")
    if entry_type == "dir":
        return DriveDirectory.from_dict(data)
    return DriveFile.from_dict(data)


@dataclass
class PaginatedList(Generic[T]):
    items: List[T]
    cursor: Optional[str] = None
    has_more: bool = False
    response_at: Optional[int] = None

    def __iter__(self) -> Iterator[T]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> T:
        return self.items[index]


def iter_paginated(
    fetch_page: Callable[..., PaginatedList[T]],
    *args: Any,
    **kwargs: Any,
) -> Iterator[T]:
    """Yield all items across cursor pages for a list_* style method."""
    cursor = kwargs.pop("cursor", None)
    while True:
        page = fetch_page(*args, cursor=cursor, **kwargs)
        yield from page.items
        if not page.has_more or not page.cursor:
            break
        cursor = page.cursor
