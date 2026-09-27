from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

from .enums import Order, OrderBy
from .models import DriveEntry, PaginatedList
from .queries import ListQuery

JsonDict = Dict[str, Any]
WithParam = Union[str, Sequence[str]]


class FavoritesMixin:
    """Favorite file listing and mutation endpoints."""

    def list_favorites(
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
        payload = self.json_request("GET", self.url(3, "files/favorites"), params=params)
        return self.paginated_entries(payload)

    def favorite(self, file_id: Union[str, int]) -> bool:
        payload = self.json_request("POST", self.url(2, f"files/{file_id}/favorite"))
        data = self.data(payload)
        return True if data is None else bool(data)

    def unfavorite(self, file_id: Union[str, int]) -> bool:
        payload = self.json_request("DELETE", self.url(2, f"files/{file_id}/favorite"))
        data = self.data(payload)
        return True if data is None else bool(data)

    def add_favorite(self, file_id: Union[str, int]) -> bool:
        return self.favorite(file_id)

    def remove_favorite(self, file_id: Union[str, int]) -> bool:
        return self.unfavorite(file_id)
