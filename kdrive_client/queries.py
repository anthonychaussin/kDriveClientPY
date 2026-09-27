from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Union

from .enums import EntryType, Order, OrderBy, QueryScope, SearchDepth


class ItemIncludes(str, Enum):
    """Common `with=` values for file/directory responses."""

    CAPABILITIES = "capabilities"
    CATEGORIES = "categories"
    CONVERSION = "conversion_capabilities"
    DROPBOX = "dropbox"
    ETAG = "etag"
    HASH = "hash"
    IS_FAVORITE = "is_favorite"
    LOCK = "lock"
    PATH = "path"
    SHARELINK = "sharelink"
    SORTED_NAME = "sorted_name"
    USERS = "users"
    TEAMS = "teams"
    VERSION = "version"


@dataclass
class ListQuery:
    cursor: Optional[str] = None
    limit: int = 100
    order_by: Optional[Union[OrderBy, str, Sequence[Union[OrderBy, str]]]] = None
    order: Optional[Union[Order, str]] = None
    type: Optional[Union[EntryType, str, Sequence[Union[EntryType, str]]]] = None
    depth: Optional[Union[SearchDepth, str]] = None
    includes: Optional[Union[ItemIncludes, str, Sequence[Union[ItemIncludes, str]]]] = None

    def to_params(self) -> Dict[str, Any]:
        order_by = self.order_by
        if order_by is not None and not isinstance(order_by, (list, tuple)):
            order_by = [order_by]
        type_ = self.type
        if type_ is not None and not isinstance(type_, (list, tuple)):
            type_ = [type_]
        includes = self.includes
        if includes is not None and not isinstance(includes, (list, tuple)):
            includes = [includes]
        return {
            "cursor": self.cursor,
            "limit": self.limit,
            "order_by": list(order_by) if order_by is not None else None,
            "order": self.order,
            "type": list(type_) if type_ is not None else None,
            "depth": self.depth,
            "with": [i.value if isinstance(i, ItemIncludes) else i for i in includes]
            if includes is not None
            else None,
        }


@dataclass
class SearchQuery:
    query: Optional[str] = None
    name: Optional[str] = None
    query_scope: Optional[Union[QueryScope, str]] = None
    directory_id: Optional[Union[str, int]] = None
    depth: Optional[Union[SearchDepth, str]] = None
    types: Optional[Sequence[str]] = None
    extensions: Optional[Sequence[str]] = None
    author_id: Optional[int] = None
    cursor: Optional[str] = None
    limit: int = 100
    order_by: Optional[Union[OrderBy, str, Sequence[Union[OrderBy, str]]]] = None
    order: Optional[Union[Order, str]] = None
    includes: Optional[Union[ItemIncludes, str, Sequence[Union[ItemIncludes, str]]]] = None

    def to_params(self) -> Dict[str, Any]:
        order_by = self.order_by
        if order_by is not None and not isinstance(order_by, (list, tuple)):
            order_by = [order_by]
        includes = self.includes
        if includes is not None and not isinstance(includes, (list, tuple)):
            includes = [includes]
        return {
            "query": self.query,
            "name": self.name,
            "query_scope": self.query_scope,
            "directory_id": self.directory_id,
            "depth": self.depth,
            "types": list(self.types) if self.types is not None else None,
            "extensions": list(self.extensions) if self.extensions is not None else None,
            "author_id": self.author_id,
            "cursor": self.cursor,
            "limit": self.limit,
            "order_by": list(order_by) if order_by is not None else None,
            "order": self.order,
            "with": [i.value if isinstance(i, ItemIncludes) else i for i in includes]
            if includes is not None
            else None,
        }
