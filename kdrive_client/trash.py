from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

from .enums import Order, OrderBy
from .models import CancelAction, DriveEntry, FileCount, PaginatedList
from .queries import ListQuery

JsonDict = Dict[str, Any]
WithParam = Union[str, Sequence[str]]


class TrashMixin:
    """Trash listing, restore, and permanent deletion endpoints."""

    def list_trash(
        self,
        *,
        query: Optional[ListQuery] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
        order_by: Optional[Union[OrderBy, str, Sequence[Union[OrderBy, str]]]] = None,
        order: Optional[Union[Order, str]] = None,
        with_: Optional[WithParam] = None,
    ) -> PaginatedList[DriveEntry]:
        if query is not None:
            params = self.as_params(query.to_params())
        else:
            order_by_list: Optional[List[Any]] = None
            if order_by is not None:
                order_by_list = list(order_by) if isinstance(order_by, (list, tuple)) else [order_by]
            params = self.as_params(
                {
                    "cursor": cursor,
                    "limit": limit,
                    "order_by": order_by_list,
                    "order": order,
                    "with": self.normalize_with(with_),
                }
            )
        payload = self.json_request("GET", self.url(3, "trash"), params=params)
        return self.paginated_entries(payload)

    def list_trash_children(
        self,
        dir_id: Union[str, int],
        *,
        query: Optional[ListQuery] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
        order_by: Optional[Union[OrderBy, str, Sequence[Union[OrderBy, str]]]] = None,
        order: Optional[Union[Order, str]] = None,
        with_: Optional[WithParam] = None,
    ) -> PaginatedList[DriveEntry]:
        if query is not None:
            params = self.as_params(query.to_params())
        else:
            order_by_list: Optional[List[Any]] = None
            if order_by is not None:
                order_by_list = list(order_by) if isinstance(order_by, (list, tuple)) else [order_by]
            params = self.as_params(
                {
                    "cursor": cursor,
                    "limit": limit,
                    "order_by": order_by_list,
                    "order": order,
                    "with": self.normalize_with(with_),
                }
            )
        payload = self.json_request(
            "GET",
            self.url(3, f"trash/{dir_id}/files"),
            params=params,
        )
        return self.paginated_entries(payload)

    def get_trashed_file(
        self,
        file_id: Union[str, int],
        *,
        with_: Optional[WithParam] = None,
    ) -> DriveEntry:
        params = self.as_params({"with": self.normalize_with(with_)})
        payload = self.json_request("GET", self.url(3, f"trash/{file_id}"), params=params)
        data = self.data(payload)
        if data is None and isinstance(payload.get("id"), int):
            data = payload
        return self.parse_entry(data)

    def restore(
        self,
        file_id: Union[str, int],
        destination_directory_id: Union[str, int],
    ) -> CancelAction:
        payload = self.json_request(
            "POST",
            self.url(2, f"trash/{file_id}/restore"),
            json={"destination_directory_id": int(destination_directory_id)},
        )
        return CancelAction.from_dict(self.data(payload) or {})

    def delete_permanently(self, file_id: Union[str, int]) -> bool:
        payload = self.json_request("DELETE", self.url(2, f"trash/{file_id}"))
        return bool(self.data(payload))

    def empty_trash(self) -> bool:
        payload = self.json_request("DELETE", self.url(2, "trash"))
        return bool(self.data(payload))

    def count_trash(self) -> FileCount:
        payload = self.json_request("GET", self.url(2, "trash/count"))
        data = self.data(payload)
        if not isinstance(data, dict):
            data = {
                "count": payload.get("count"),
                "files": payload.get("files"),
                "directories": payload.get("directories"),
            }
        return FileCount.from_dict(data)

    def count_trash_children(self, dir_id: Union[str, int]) -> FileCount:
        payload = self.json_request("GET", self.url(2, f"trash/{dir_id}/count"))
        data = self.data(payload)
        if not isinstance(data, dict):
            data = {
                "count": payload.get("count"),
                "files": payload.get("files"),
                "directories": payload.get("directories"),
            }
        return FileCount.from_dict(data)
