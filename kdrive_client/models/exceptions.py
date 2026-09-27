from __future__ import annotations

from typing import Any, Dict, List, Optional


class KDriveApiException(Exception):
    """Raised when the Infomaniak API returns an error or an unexpected payload."""

    def __init__(
        self,
        code: str,
        description: str,
        *,
        status: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        errors: Optional[List[Dict[str, Any]]] = None,
    ):
        self.code = code
        self.description = description
        self.status = status
        self.context = context or {}
        self.errors = errors or []
        detail = f"{code}: {description}"
        if status is not None:
            detail = f"[{status}] {detail}"
        super().__init__(detail)

    @classmethod
    def from_payload(
        cls,
        payload: Dict[str, Any],
        *,
        status: Optional[int] = None,
        fallback_text: str = "",
    ) -> "KDriveApiException":
        error = payload.get("error") or {}
        if not isinstance(error, dict):
            error = {}
        code = error.get("code") or str(status or "api_error")
        description = error.get("description") or fallback_text or "Unknown API error"
        context = error.get("context") if isinstance(error.get("context"), dict) else {}
        errors = error.get("errors") if isinstance(error.get("errors"), list) else []
        return cls(
            str(code),
            str(description),
            status=status,
            context=context,
            errors=errors,
        )
