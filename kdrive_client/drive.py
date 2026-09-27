from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

from .models import DriveInfo, KDriveApiException

JsonDict = Dict[str, Any]
WithParam = Union[str, Sequence[str]]


class DriveMixin:
    """Drive metadata, settings, users, activities, imports, and statistics."""

    drive_id: str
    base_url: str

    def list_drives(self, account_id: Union[str, int]) -> List[DriveInfo]:
        payload = self.json_request(
            "GET",
            self.account_url(2, "drive"),
            params={"account_id": account_id},
        )
        raw = self.data(payload) or []
        return [DriveInfo.from_dict(item) for item in raw]

    def get_drive(self, *, with_: Optional[WithParam] = None) -> DriveInfo:
        params = self.as_params({"with": self.normalize_with(with_)})
        payload = self.json_request(
            "GET",
            f"{self.base_url}/2/drive/{self.drive_id}",
            params=params,
        )
        data = self.data(payload)
        if not isinstance(data, dict):
            raise KDriveApiException("unexpected_payload", "Missing drive payload")
        return DriveInfo.from_dict(data)

    def update_drive(self, body: Dict[str, Any]) -> DriveInfo:
        payload = self.json_request(
            "PUT",
            f"{self.base_url}/2/drive/{self.drive_id}",
            json=body,
        )
        data = self.data(payload)
        if not isinstance(data, dict):
            raise KDriveApiException("unexpected_payload", "Missing drive payload")
        return DriveInfo.from_dict(data)

    def wake(self) -> bool:
        payload = self.json_request("POST", self.url(3, "wake"))
        data = self.data(payload)
        return True if data is None else bool(data)

    # --- Settings ---------------------------------------------------------

    def get_settings(self, name: Optional[str] = None) -> Dict[str, Any]:
        path = f"settings/{name}" if name else "settings"
        payload = self.json_request("GET", self.url(2, path))
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def update_settings(
        self,
        body: Dict[str, Any],
        *,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        path = f"settings/{name}" if name else "settings"
        payload = self.json_request("PUT", self.url(2, path), json=body)
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def get_ai_settings(self) -> Dict[str, Any]:
        return self.get_settings("ai")

    def update_ai_settings(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.update_settings(body, name="ai")

    def get_link_settings(self) -> Dict[str, Any]:
        return self.get_settings("link")

    def update_link_settings(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.update_settings(body, name="link")

    def get_office_settings(self) -> Dict[str, Any]:
        return self.get_settings("office")

    def update_office_settings(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.update_settings(body, name="office")

    def get_trash_settings(self) -> Dict[str, Any]:
        return self.get_settings("trash")

    def update_trash_settings(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return self.update_settings(body, name="trash")

    def get_preferences(self) -> Dict[str, Any]:
        payload = self.json_request("GET", self.url(2, "preferences"))
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def patch_preferences(self, body: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.json_request("PATCH", self.url(2, "preferences"), json=body)
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    # --- Users ------------------------------------------------------------

    def list_users(self, **params: Any) -> Any:
        payload = self.json_request(
            "GET",
            self.url(3, "users"),
            params=self.as_params(params) or None,
        )
        return self.data(payload)

    def get_user(self, user_id: Union[str, int], **params: Any) -> Dict[str, Any]:
        payload = self.json_request(
            "GET",
            self.url(2, f"users/{user_id}"),
            params=self.as_params(params) or None,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def create_user(self, body: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.json_request("POST", self.url(2, "users"), json=body)
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def update_user(
        self,
        user_id: Union[str, int],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "PUT",
            self.url(2, f"users/{user_id}"),
            json=body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def delete_user(self, user_id: Union[str, int]) -> bool:
        payload = self.json_request("DELETE", self.url(2, f"users/{user_id}"))
        data = self.data(payload)
        return True if data is None else bool(data)

    def lock_user(self, user_id: Union[str, int]) -> bool:
        payload = self.json_request("POST", self.url(2, f"users/{user_id}/lock"))
        data = self.data(payload)
        return True if data is None else bool(data)

    def unlock_user(self, user_id: Union[str, int]) -> bool:
        payload = self.json_request("POST", self.url(2, f"users/{user_id}/unlock"))
        data = self.data(payload)
        return True if data is None else bool(data)

    # --- Activities / reports ---------------------------------------------

    def list_drive_activities(self, **params: Any) -> Any:
        payload = self.json_request(
            "GET",
            self.url(2, "activity"),
            params=self.as_params(params) or None,
        )
        return self.data(payload)

    def list_activity_reports(self, **params: Any) -> Any:
        payload = self.json_request(
            "GET",
            self.url(2, "activity/report"),
            params=self.as_params(params) or None,
        )
        return self.data(payload)

    def get_activity_report(self, report_id: Union[str, int]) -> Dict[str, Any]:
        payload = self.json_request("GET", self.url(2, f"activity/report/{report_id}"))
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def create_activity_report(self, body: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.json_request("POST", self.url(2, "activity/report"), json=body)
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def update_activity_report(
        self,
        report_id: Union[str, int],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "PUT",
            self.url(2, f"activity/report/{report_id}"),
            json=body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def delete_activity_report(self, report_id: Union[str, int]) -> bool:
        payload = self.json_request(
            "DELETE",
            self.url(2, f"activity/report/{report_id}"),
        )
        data = self.data(payload)
        return True if data is None else bool(data)

    def export_activity_report(self, report_id: Union[str, int]) -> Any:
        payload = self.json_request(
            "GET",
            self.url(2, f"activity/report/{report_id}/export"),
        )
        return self.data(payload)

    # --- Statistics -------------------------------------------------------

    def get_statistics(self, *, name: Optional[str] = None, **params: Any) -> Any:
        path = f"statistics/{name}" if name else "statistics"
        payload = self.json_request(
            "GET",
            self.url(2, path),
            params=self.as_params(params) or None,
        )
        return self.data(payload)

    def get_activity_statistics(self, **params: Any) -> Any:
        return self.get_statistics(name="activities", **params)

    def get_activity_statistics_export(self, **params: Any) -> Any:
        return self.get_statistics(name="activities/export", **params)

    def get_size_statistics(self, **params: Any) -> Any:
        return self.get_statistics(name="sizes", **params)

    def get_size_statistics_export(self, **params: Any) -> Any:
        return self.get_statistics(name="sizes/export", **params)

    def get_link_activity_statistics(self, **params: Any) -> Any:
        return self.get_statistics(name="activities/links", **params)

    def get_user_activity_statistics(self, **params: Any) -> Any:
        return self.get_statistics(name="activities/users", **params)

    def get_shared_files_activity_statistics(self, **params: Any) -> Any:
        return self.get_statistics(name="activities/shared_files", **params)

    # --- Imports ----------------------------------------------------------

    def list_imports(self, **params: Any) -> Any:
        payload = self.json_request(
            "GET",
            self.url(2, "imports"),
            params=self.as_params(params) or None,
        )
        return self.data(payload)

    def clear_imports_history(self) -> bool:
        payload = self.json_request("DELETE", self.url(2, "imports"))
        data = self.data(payload)
        return True if data is None else bool(data)

    def list_oauth_import_drives(self, **params: Any) -> Any:
        payload = self.json_request(
            "GET",
            self.url(2, "imports/oauth/drives"),
            params=self.as_params(params) or None,
        )
        return self.data(payload)

    def get_import(self, import_id: Union[str, int]) -> Dict[str, Any]:
        payload = self.json_request("GET", self.url(2, f"imports/{import_id}"))
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def cancel_import(self, import_id: Union[str, int]) -> bool:
        payload = self.json_request(
            "POST",
            self.url(2, f"imports/{import_id}/cancel"),
        )
        data = self.data(payload)
        return True if data is None else bool(data)

    def delete_import(self, import_id: Union[str, int]) -> bool:
        payload = self.json_request("DELETE", self.url(2, f"imports/{import_id}"))
        data = self.data(payload)
        return True if data is None else bool(data)

    def start_oauth_import(self, body: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.json_request("POST", self.url(2, "imports/oauth"), json=body)
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def start_kdrive_import(self, body: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.json_request("POST", self.url(2, "imports/kdrive"), json=body)
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def start_webdav_import(self, body: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.json_request("POST", self.url(2, "imports/webdav"), json=body)
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def start_sharelink_import(self, body: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.json_request("POST", self.url(2, "imports/sharelink"), json=body)
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def copy_to_drive(
        self,
        file_id: Union[str, int],
        body: Dict[str, Any],
    ) -> Any:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/copy-to-drive"),
            json=body,
        )
        return self.data(payload)
