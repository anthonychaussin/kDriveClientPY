from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

JsonDict = Dict[str, Any]


class CommentsMixin:
    """File comment CRUD and like endpoints (API v2)."""

    def list_comments(
        self,
        file_id: Union[str, int],
        *,
        cursor: Optional[str] = None,
        limit: int = 100,
        with_: Optional[Union[str, List[str]]] = None,
    ) -> Any:
        params = self.as_params(
            {
                "cursor": cursor,
                "limit": limit,
                "with": self.normalize_with(with_),
            }
        )
        payload = self.json_request(
            "GET",
            self.url(2, f"files/{file_id}/comments"),
            params=params,
        )
        return self.data(payload)

    def get_comment(
        self,
        file_id: Union[str, int],
        comment_id: Union[str, int],
        *,
        with_: Optional[Union[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        params = self.as_params({"with": self.normalize_with(with_)})
        payload = self.json_request(
            "GET",
            self.url(2, f"files/{file_id}/comments/{comment_id}"),
            params=params or None,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def create_comment(
        self,
        file_id: Union[str, int],
        body: Union[str, Dict[str, Any]],
        **extra: Any,
    ) -> Dict[str, Any]:
        payload_body: Dict[str, Any]
        if isinstance(body, str):
            payload_body = {"body": body, **extra}
        else:
            payload_body = {**body, **extra}
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/comments"),
            json=payload_body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def reply_comment(
        self,
        file_id: Union[str, int],
        comment_id: Union[str, int],
        body: Union[str, Dict[str, Any]],
        **extra: Any,
    ) -> Dict[str, Any]:
        payload_body: Dict[str, Any]
        if isinstance(body, str):
            payload_body = {"body": body, **extra}
        else:
            payload_body = {**body, **extra}
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/comments/{comment_id}"),
            json=payload_body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def update_comment(
        self,
        file_id: Union[str, int],
        comment_id: Union[str, int],
        body: Union[str, Dict[str, Any]],
        **extra: Any,
    ) -> Dict[str, Any]:
        payload_body: Dict[str, Any]
        if isinstance(body, str):
            payload_body = {"body": body, **extra}
        else:
            payload_body = {**body, **extra}
        payload = self.json_request(
            "PUT",
            self.url(2, f"files/{file_id}/comments/{comment_id}"),
            json=payload_body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def delete_comment(
        self,
        file_id: Union[str, int],
        comment_id: Union[str, int],
    ) -> bool:
        payload = self.json_request(
            "DELETE",
            self.url(2, f"files/{file_id}/comments/{comment_id}"),
        )
        data = self.data(payload)
        return True if data is None else bool(data)

    def like_comment(
        self,
        file_id: Union[str, int],
        comment_id: Union[str, int],
    ) -> bool:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/comments/{comment_id}/like"),
        )
        data = self.data(payload)
        return True if data is None else bool(data)

    def unlike_comment(
        self,
        file_id: Union[str, int],
        comment_id: Union[str, int],
    ) -> bool:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/comments/{comment_id}/unlike"),
        )
        data = self.data(payload)
        return True if data is None else bool(data)
