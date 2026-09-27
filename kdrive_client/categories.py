from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

JsonDict = Dict[str, Any]


class CategoriesMixin:
    """Drive category management and file categorization endpoints."""

    def list_categories(self, *, with_: Optional[Union[str, Sequence[str]]] = None) -> Any:
        params = self.as_params({"with": self.normalize_with(with_)})
        payload = self.json_request("GET", self.url(2, "categories"), params=params or None)
        return self.data(payload)

    def create_category(self, body: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.json_request("POST", self.url(2, "categories"), json=body)
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def update_category(
        self,
        category_id: Union[str, int],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "PUT",
            self.url(2, f"categories/{category_id}"),
            json=body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def delete_category(self, category_id: Union[str, int]) -> bool:
        payload = self.json_request("DELETE", self.url(2, f"categories/{category_id}"))
        data = self.data(payload)
        return True if data is None else bool(data)

    def get_category_rights(self) -> Dict[str, Any]:
        payload = self.json_request("GET", self.url(2, "categories/rights"))
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def set_category_rights(self, body: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.json_request("PUT", self.url(2, "categories/rights"), json=body)
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def add_category(
        self,
        file_id: Union[str, int],
        category_id: Union[str, int],
    ) -> bool:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/categories/{category_id}"),
        )
        data = self.data(payload)
        return True if data is None else bool(data)

    def remove_category(
        self,
        file_id: Union[str, int],
        category_id: Union[str, int],
    ) -> bool:
        payload = self.json_request(
            "DELETE",
            self.url(2, f"files/{file_id}/categories/{category_id}"),
        )
        data = self.data(payload)
        return True if data is None else bool(data)

    def remove_all_categories(self, file_id: Union[str, int]) -> bool:
        payload = self.json_request(
            "DELETE",
            self.url(2, f"files/{file_id}/categories"),
        )
        data = self.data(payload)
        return True if data is None else bool(data)

    def bulk_add_categories(self, body: Dict[str, Any]) -> Any:
        payload = self.json_request(
            "POST",
            self.url(2, "files/categories"),
            json=body,
        )
        return self.data(payload)

    def bulk_remove_categories(self, body: Dict[str, Any]) -> Any:
        payload = self.json_request(
            "DELETE",
            self.url(2, "files/categories"),
            json=body,
        )
        return self.data(payload)

    def ai_feedback(self, body: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.json_request(
            "POST",
            self.url(2, "categories/ai/feedback"),
            json=body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}
