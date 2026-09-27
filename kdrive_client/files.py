from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Sequence, Union

from .enums import ConflictMode, EntryType, Order, OrderBy, QueryScope, SearchDepth
from .models import (
    CancelAction,
    DriveDirectory,
    DriveEntry,
    DriveFile,
    FileCount,
    PaginatedList,
    iter_paginated,
)
from .queries import ListQuery, SearchQuery

JsonDict = Dict[str, Any]
WithParam = Union[str, Sequence[str]]


class FilesMixin:
    """File and directory listing, mutation, search, and version endpoints."""

    def get_file(
        self,
        file_id: Union[str, int],
        *,
        with_: Optional[WithParam] = None,
    ) -> DriveEntry:
        params = self.as_params({"with": self.normalize_with(with_)})
        payload = self.json_request("GET", self.url(3, f"files/{file_id}"), params=params)
        return self.parse_entry(self.data(payload))

    def get_item(
        self,
        file_id: Union[str, int],
        *,
        with_: Optional[WithParam] = None,
    ) -> DriveEntry:
        return self.get_file(file_id, with_=with_)

    def list_files(
        self,
        directory_id: Union[str, int] = 1,
        *,
        query: Optional[ListQuery] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
        order_by: Optional[Union[OrderBy, str, Sequence[Union[OrderBy, str]]]] = None,
        order: Optional[Union[Order, str]] = None,
        type: Optional[Union[EntryType, str, Sequence[Union[EntryType, str]]]] = None,
        depth: Optional[Union[SearchDepth, str]] = None,
        with_: Optional[WithParam] = None,
    ) -> PaginatedList[DriveEntry]:
        if query is not None:
            params = self.as_params(query.to_params())
        else:
            order_by_list: Optional[List[Any]] = None
            if order_by is not None:
                order_by_list = list(order_by) if isinstance(order_by, (list, tuple)) else [order_by]
            type_list: Optional[List[Any]] = None
            if type is not None:
                type_list = list(type) if isinstance(type, (list, tuple)) else [type]
            params = self.as_params(
                {
                    "cursor": cursor,
                    "limit": limit,
                    "order_by": order_by_list,
                    "order": order,
                    "type": type_list,
                    "depth": depth,
                    "with": self.normalize_with(with_),
                }
            )
        payload = self.json_request(
            "GET",
            self.url(3, f"files/{directory_id}/files"),
            params=params,
        )
        return self.paginated_entries(payload)

    def iter_files(
        self,
        directory_id: Union[str, int] = 1,
        **kwargs: Any,
    ) -> Iterator[DriveEntry]:
        return iter_paginated(self.list_files, directory_id, **kwargs)

    def list_all_files(
        self,
        directory_id: Union[str, int] = 1,
        **kwargs: Any,
    ) -> List[DriveEntry]:
        return list(self.iter_files(directory_id, **kwargs))

    def create_directory(
        self,
        parent_id: Union[str, int],
        name: str,
        *,
        color: Optional[str] = None,
        only_for_me: Optional[bool] = None,
        relative_path: Optional[str] = None,
    ) -> DriveDirectory:
        body: Dict[str, Any] = {"name": name}
        if color is not None:
            body["color"] = color
        if only_for_me is not None:
            body["only_for_me"] = only_for_me
        if relative_path is not None:
            body["relative_path"] = relative_path

        payload = self.json_request(
            "POST",
            self.url(3, f"files/{parent_id}/directory"),
            json=body,
        )
        entry = self.parse_entry(self.data(payload), expected="dir")
        assert isinstance(entry, DriveDirectory)
        return entry

    def create_folder(
        self,
        parent_id: Union[str, int],
        name: str,
        **kwargs: Any,
    ) -> DriveDirectory:
        return self.create_directory(parent_id, name, **kwargs)

    def create_team_directory(
        self,
        name: str,
        *,
        for_all_user: bool = False,
        color: Optional[str] = None,
        with_: Optional[WithParam] = None,
    ) -> DriveDirectory:
        body: Dict[str, Any] = {"name": name, "for_all_user": for_all_user}
        if color is not None:
            body["color"] = color
        params = self.as_params({"with": self.normalize_with(with_)})
        payload = self.json_request(
            "POST",
            self.url(3, "files/team_directory"),
            json=body,
            params=params or None,
        )
        data = self.data(payload)
        if data is None and isinstance(payload.get("id"), int):
            data = payload
        entry = self.parse_entry(data, expected="dir")
        assert isinstance(entry, DriveDirectory)
        return entry

    def create_file(
        self,
        parent_id: Union[str, int],
        name: str,
        *,
        with_: Optional[WithParam] = None,
        **extra: Any,
    ) -> DriveFile:
        body: Dict[str, Any] = {"name": name, **extra}
        params = self.as_params({"with": self.normalize_with(with_)})
        payload = self.json_request(
            "POST",
            self.url(3, f"files/{parent_id}/file"),
            json=body,
            params=params or None,
        )
        data = self.data(payload)
        if data is None and isinstance(payload.get("id"), int):
            data = payload
        entry = self.parse_entry(data, expected="file")
        assert isinstance(entry, DriveFile)
        return entry

    def rename(self, file_id: Union[str, int], name: str) -> CancelAction:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/rename"),
            json={"name": name},
        )
        return CancelAction.from_dict(self.data(payload) or {})

    def move(
        self,
        file_id: Union[str, int],
        destination_id: Union[str, int],
        *,
        conflict: ConflictMode = ConflictMode.ERROR,
        name: Optional[str] = None,
    ) -> CancelAction:
        body: Dict[str, Any] = {"conflict": self.enum_value(conflict)}
        if name is not None:
            body["name"] = name
        payload = self.json_request(
            "POST",
            self.url(3, f"files/{file_id}/move/{destination_id}"),
            json=body,
        )
        return CancelAction.from_dict(self.data(payload) or {})

    def copy(
        self,
        file_id: Union[str, int],
        destination_id: Union[str, int],
        *,
        conflict: ConflictMode = ConflictMode.RENAME,
        name: Optional[str] = None,
        with_: Optional[WithParam] = None,
    ) -> DriveEntry:
        body: Dict[str, Any] = {"conflict": self.enum_value(conflict)}
        if name is not None:
            body["name"] = name
        params = self.as_params({"with": self.normalize_with(with_)})
        payload = self.json_request(
            "POST",
            self.url(3, f"files/{file_id}/copy/{destination_id}"),
            json=body,
            params=params,
        )
        return self.parse_entry(self.data(payload))

    def duplicate(
        self,
        file_id: Union[str, int],
        *,
        name: Optional[str] = None,
        with_: Optional[WithParam] = None,
    ) -> DriveEntry:
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        params = self.as_params({"with": self.normalize_with(with_)})
        payload = self.json_request(
            "POST",
            self.url(3, f"files/{file_id}/duplicate"),
            json=body or None,
            params=params,
        )
        data = self.data(payload)
        if data is None and isinstance(payload.get("id"), int):
            data = payload
        return self.parse_entry(data)

    def count(
        self,
        file_id: Union[str, int],
        *,
        depth: Optional[str] = None,
    ) -> FileCount:
        params = self.as_params({"depth": depth})
        payload = self.json_request(
            "GET",
            self.url(3, f"files/{file_id}/count"),
            params=params,
        )
        data = self.data(payload)
        if not isinstance(data, dict):
            data = {
                "count": payload.get("count"),
                "files": payload.get("files"),
                "directories": payload.get("directories"),
            }
        return FileCount.from_dict(data)

    def trash(self, file_id: Union[str, int]) -> CancelAction:
        payload = self.json_request("DELETE", self.url(2, f"files/{file_id}"))
        return CancelAction.from_dict(self.data(payload) or {})

    def cancel(
        self,
        cancel_id: Optional[Union[str, CancelAction, Sequence[Union[str, CancelAction]]]] = None,
        *,
        cancel_ids: Optional[Sequence[Union[str, CancelAction]]] = None,
    ) -> bool:
        ids: List[str] = []
        if cancel_ids is not None:
            for item in cancel_ids:
                ids.append(item.cancel_id if isinstance(item, CancelAction) else str(item))
        elif isinstance(cancel_id, (list, tuple)):
            for item in cancel_id:
                ids.append(item.cancel_id if isinstance(item, CancelAction) else str(item))
        elif isinstance(cancel_id, CancelAction):
            ids.append(cancel_id.cancel_id)
        elif cancel_id is not None:
            ids.append(str(cancel_id))
        else:
            raise ValueError("Provide cancel_id or cancel_ids")

        body: Dict[str, Any]
        if len(ids) == 1:
            body = {"cancel_id": ids[0]}
        else:
            body = {"cancel_ids": ids}
        payload = self.json_request(
            "POST",
            self.url(2, "cancel"),
            json=body,
        )
        data = self.data(payload)
        return True if data is None else bool(data)

    def undo(
        self,
        cancel_id: Optional[Union[str, CancelAction, Sequence[Union[str, CancelAction]]]] = None,
        *,
        cancel_ids: Optional[Sequence[Union[str, CancelAction]]] = None,
    ) -> bool:
        return self.cancel(cancel_id, cancel_ids=cancel_ids)

    def _search_path(
        self,
        path: str,
        *,
        query: Optional[Union[str, SearchQuery]] = None,
        name: Optional[str] = None,
        query_scope: Optional[Union[QueryScope, str]] = None,
        directory_id: Optional[Union[str, int]] = None,
        depth: Optional[Union[SearchDepth, str]] = None,
        types: Optional[Sequence[str]] = None,
        extensions: Optional[Sequence[str]] = None,
        author_id: Optional[int] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
        order_by: Optional[Union[OrderBy, str, Sequence[Union[OrderBy, str]]]] = None,
        order: Optional[Union[Order, str]] = None,
        with_: Optional[WithParam] = None,
    ) -> PaginatedList[DriveEntry]:
        if isinstance(query, SearchQuery):
            params = self.as_params(query.to_params())
        else:
            order_by_list: Optional[List[Any]] = None
            if order_by is not None:
                order_by_list = list(order_by) if isinstance(order_by, (list, tuple)) else [order_by]
            params = self.as_params(
                {
                    "query": query,
                    "name": name,
                    "query_scope": query_scope,
                    "directory_id": directory_id,
                    "depth": depth,
                    "types": list(types) if types is not None else None,
                    "extensions": list(extensions) if extensions is not None else None,
                    "author_id": author_id,
                    "cursor": cursor,
                    "limit": limit,
                    "order_by": order_by_list,
                    "order": order,
                    "with": self.normalize_with(with_),
                }
            )
        payload = self.json_request("GET", self.url(3, path), params=params)
        return self.paginated_entries(payload)

    def search(
        self,
        *,
        query: Optional[Union[str, SearchQuery]] = None,
        name: Optional[str] = None,
        query_scope: Optional[Union[QueryScope, str]] = None,
        directory_id: Optional[Union[str, int]] = None,
        depth: Optional[Union[SearchDepth, str]] = None,
        types: Optional[Sequence[str]] = None,
        extensions: Optional[Sequence[str]] = None,
        author_id: Optional[int] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
        order_by: Optional[Union[OrderBy, str, Sequence[Union[OrderBy, str]]]] = None,
        order: Optional[Union[Order, str]] = None,
        with_: Optional[WithParam] = None,
    ) -> PaginatedList[DriveEntry]:
        return self._search_path(
            "files/search",
            query=query,
            name=name,
            query_scope=query_scope,
            directory_id=directory_id,
            depth=depth,
            types=types,
            extensions=extensions,
            author_id=author_id,
            cursor=cursor,
            limit=limit,
            order_by=order_by,
            order=order,
            with_=with_,
        )

    def search_favorites(self, **kwargs: Any) -> PaginatedList[DriveEntry]:
        return self._search_path("files/search/favorites", **kwargs)

    def search_links(self, **kwargs: Any) -> PaginatedList[DriveEntry]:
        return self._search_path("files/search/links", **kwargs)

    def search_trash(self, **kwargs: Any) -> PaginatedList[DriveEntry]:
        return self._search_path("trash/search", **kwargs)

    def search_my_shared(self, **kwargs: Any) -> PaginatedList[DriveEntry]:
        return self._search_path("files/search/my_shared", **kwargs)

    def search_shared_with_me(self, **kwargs: Any) -> PaginatedList[DriveEntry]:
        return self._search_path("files/search/shared_with_me", **kwargs)

    def search_dropboxes(self, **kwargs: Any) -> PaginatedList[DriveEntry]:
        return self._search_path("files/search/dropboxes", **kwargs)

    def _list_collection(
        self,
        path: str,
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
        payload = self.json_request("GET", self.url(3, path), params=params)
        return self.paginated_entries(payload)

    def list_recents(
        self,
        *,
        query: Optional[ListQuery] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
        with_: Optional[WithParam] = None,
    ) -> PaginatedList[DriveEntry]:
        return self._list_collection(
            "files/last_modified",
            query=query,
            cursor=cursor,
            limit=limit,
            with_=with_,
        )

    def list_recent_files(
        self,
        *,
        query: Optional[ListQuery] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
        with_: Optional[WithParam] = None,
    ) -> PaginatedList[DriveEntry]:
        return self._list_collection(
            "files/recents",
            query=query,
            cursor=cursor,
            limit=limit,
            with_=with_,
        )

    def list_my_shared(
        self,
        *,
        query: Optional[ListQuery] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
        order_by: Optional[Union[OrderBy, str, Sequence[Union[OrderBy, str]]]] = None,
        order: Optional[Union[Order, str]] = None,
        with_: Optional[WithParam] = None,
    ) -> PaginatedList[DriveEntry]:
        return self._list_collection(
            "files/my_shared",
            query=query,
            cursor=cursor,
            limit=limit,
            order_by=order_by,
            order=order,
            with_=with_,
        )

    def list_shared_with_me(
        self,
        *,
        query: Optional[ListQuery] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
        order_by: Optional[Union[OrderBy, str, Sequence[Union[OrderBy, str]]]] = None,
        order: Optional[Union[Order, str]] = None,
        with_: Optional[WithParam] = None,
    ) -> PaginatedList[DriveEntry]:
        return self._list_collection(
            "files/shared_with_me",
            query=query,
            cursor=cursor,
            limit=limit,
            order_by=order_by,
            order=order,
            with_=with_,
        )

    def list_dropboxes(
        self,
        *,
        query: Optional[ListQuery] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
        with_: Optional[WithParam] = None,
    ) -> PaginatedList[DriveEntry]:
        return self._list_collection(
            "files/dropboxes",
            query=query,
            cursor=cursor,
            limit=limit,
            with_=with_,
        )

    def list_largest(
        self,
        *,
        query: Optional[ListQuery] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
        with_: Optional[WithParam] = None,
    ) -> PaginatedList[DriveEntry]:
        return self._list_collection(
            "files/largest",
            query=query,
            cursor=cursor,
            limit=limit,
            with_=with_,
        )

    def list_most_versions(
        self,
        *,
        query: Optional[ListQuery] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
        with_: Optional[WithParam] = None,
    ) -> PaginatedList[DriveEntry]:
        return self._list_collection(
            "files/most_versions",
            query=query,
            cursor=cursor,
            limit=limit,
            with_=with_,
        )

    def list_links(
        self,
        *,
        query: Optional[ListQuery] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
        with_: Optional[WithParam] = None,
    ) -> PaginatedList[DriveEntry]:
        return self._list_collection(
            "files/links",
            query=query,
            cursor=cursor,
            limit=limit,
            with_=with_,
        )

    def find_by_name(
        self,
        parent_id: Union[str, int],
        name: str,
        *,
        with_: Optional[WithParam] = None,
    ) -> DriveEntry:
        params = self.as_params({"name": name, "with": self.normalize_with(with_)})
        payload = self.json_request(
            "GET",
            self.url(3, f"files/{parent_id}/name"),
            params=params,
        )
        return self.parse_entry(self.data(payload))

    def unlock(
        self,
        file_id: Union[str, int],
        *,
        path: Optional[str] = None,
        token: Optional[str] = None,
    ) -> bool:
        params = self.as_params({"path": path, "token": token})
        payload = self.json_request(
            "DELETE",
            self.url(3, f"files/{file_id}/lock"),
            params=params or None,
        )
        data = self.data(payload)
        return True if data is None else bool(data)

    def convert(
        self,
        file_id: Union[str, int],
        *,
        with_: Optional[WithParam] = None,
        password: Optional[str] = None,
    ) -> DriveEntry:
        params = self.as_params({"with": self.normalize_with(with_)})
        headers = {"x-kdrive-file-password": password} if password else None
        payload = self.json_request(
            "POST",
            self.url(3, f"files/{file_id}/convert"),
            params=params or None,
            headers=headers,
        )
        data = self.data(payload)
        if data is None and isinstance(payload.get("id"), int):
            data = payload
        return self.parse_entry(data)

    def files_exist(self, body: Dict[str, Any]) -> Any:
        payload = self.json_request("POST", self.url(2, "files/exists"), json=body)
        return self.data(payload)

    def touch_last_modified(
        self,
        file_id: Union[str, int],
        last_modified_at: Union[int, str],
    ) -> Any:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/last-modified"),
            json={"last_modified_at": last_modified_at},
        )
        return self.data(payload)

    def get_hash(self, file_id: Union[str, int]) -> Any:
        payload = self.json_request("GET", self.url(2, f"files/{file_id}/hash"))
        data = self.data(payload)
        if data is None and "hash" in payload:
            return payload.get("hash")
        return data

    def get_sizes(
        self,
        file_id: Union[str, int],
        *,
        depth: Optional[str] = None,
    ) -> Dict[str, Any]:
        params = self.as_params({"depth": depth})
        payload = self.json_request(
            "GET",
            self.url(2, f"files/{file_id}/sizes"),
            params=params or None,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def list_versions(self, file_id: Union[str, int]) -> Any:
        payload = self.json_request("GET", self.url(3, f"files/{file_id}/versions"))
        return self.data(payload)

    def restore_version(
        self,
        file_id: Union[str, int],
        version_id: Union[str, int],
    ) -> Any:
        payload = self.json_request(
            "POST",
            self.url(3, f"files/{file_id}/versions/{version_id}/restore"),
        )
        return self.data(payload)

    def restore_version_to(
        self,
        file_id: Union[str, int],
        version_id: Union[str, int],
        dest_id: Union[str, int],
    ) -> Any:
        payload = self.json_request(
            "POST",
            self.url(3, f"files/{file_id}/versions/{version_id}/restore/{dest_id}"),
        )
        return self.data(payload)

    def list_versions_v2(self, file_id: Union[str, int]) -> Any:
        payload = self.json_request("GET", self.url(2, f"files/{file_id}/versions"))
        return self.data(payload)

    def get_version_v2(
        self,
        file_id: Union[str, int],
        version_id: Union[str, int],
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "GET",
            self.url(2, f"files/{file_id}/versions/{version_id}"),
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def delete_version_v2(
        self,
        file_id: Union[str, int],
        version_id: Union[str, int],
    ) -> bool:
        payload = self.json_request(
            "DELETE",
            self.url(2, f"files/{file_id}/versions/{version_id}"),
        )
        data = self.data(payload)
        return True if data is None else bool(data)

    def delete_all_versions(self, file_id: Union[str, int]) -> bool:
        payload = self.json_request("DELETE", self.url(2, f"files/{file_id}/versions"))
        data = self.data(payload)
        return True if data is None else bool(data)

    def restore_version_v2(
        self,
        file_id: Union[str, int],
        version_id: Union[str, int],
    ) -> Any:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/versions/{version_id}/restore"),
        )
        return self.data(payload)

    def set_current_version(
        self,
        file_id: Union[str, int],
        version_id: Union[str, int],
    ) -> Any:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/versions/{version_id}/current"),
        )
        return self.data(payload)

    def update_version_v2(
        self,
        file_id: Union[str, int],
        version_id: Union[str, int],
        body: Dict[str, Any],
    ) -> Any:
        payload = self.json_request(
            "PUT",
            self.url(2, f"files/{file_id}/versions/{version_id}"),
            json=body,
        )
        return self.data(payload)

    def build_archive(self, body: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.json_request("POST", self.url(3, "files/archives"), json=body)
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def list_activities(
        self,
        file_id: Optional[Union[str, int]] = None,
        *,
        cursor: Optional[str] = None,
        limit: int = 100,
        **params: Any,
    ) -> Any:
        query = self.as_params({"cursor": cursor, "limit": limit, **params})
        path = f"files/{file_id}/activities" if file_id is not None else "files/activities"
        payload = self.json_request("GET", self.url(3, path), params=query)
        return self.data(payload)
