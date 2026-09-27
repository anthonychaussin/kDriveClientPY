from __future__ import annotations

from typing import Any, Dict, Optional, Union

from .models import KDriveApiException, ShareLink

JsonDict = Dict[str, Any]


class SharesMixin:
    """Share links, dropboxes, ACL, and drive invitation endpoints."""

    # --- Share links ------------------------------------------------------

    def get_share_link(self, file_id: Union[str, int]) -> ShareLink:
        payload = self.json_request("GET", self.url(2, f"files/{file_id}/link"))
        data = self.data(payload)
        if not isinstance(data, dict):
            raise KDriveApiException("unexpected_payload", "Missing share link payload")
        return ShareLink.from_dict(data)

    def create_share_link(
        self,
        file_id: Union[str, int],
        *,
        right: str = "public",
        password: Optional[str] = None,
        valid_until: Optional[int] = None,
        can_download: Optional[bool] = None,
        can_edit: Optional[bool] = None,
        can_see_stats: Optional[bool] = None,
        can_comment: Optional[bool] = None,
        **extra: Any,
    ) -> ShareLink:
        body: Dict[str, Any] = {"right": right, **extra}
        if password is not None:
            body["password"] = password
        if valid_until is not None:
            body["valid_until"] = valid_until
        if can_download is not None:
            body["can_download"] = can_download
        if can_edit is not None:
            body["can_edit"] = can_edit
        if can_see_stats is not None:
            body["can_see_stats"] = can_see_stats
        if can_comment is not None:
            body["can_comment"] = can_comment
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/link"),
            json=body,
        )
        data = self.data(payload)
        if not isinstance(data, dict):
            raise KDriveApiException("unexpected_payload", "Missing share link payload")
        return ShareLink.from_dict(data)

    def update_share_link(
        self,
        file_id: Union[str, int],
        body: Dict[str, Any],
    ) -> ShareLink:
        payload = self.json_request(
            "PUT",
            self.url(2, f"files/{file_id}/link"),
            json=body,
        )
        data = self.data(payload)
        if not isinstance(data, dict):
            raise KDriveApiException("unexpected_payload", "Missing share link payload")
        return ShareLink.from_dict(data)

    def delete_share_link(self, file_id: Union[str, int]) -> bool:
        payload = self.json_request("DELETE", self.url(2, f"files/{file_id}/link"))
        data = self.data(payload)
        return True if data is None else bool(data)

    def invite_share_link(
        self,
        file_id: Union[str, int],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/link/invite"),
            json=body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def create_share_link_archive(
        self,
        share_uuid: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """POST /2/app/{drive_id}/share/{share_uuid}/archive"""
        payload = self.json_request(
            "POST",
            f"{self.base_url}/2/app/{self.drive_id}/share/{share_uuid}/archive",
            json=body or {},
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def download_share_link_archive(
        self,
        share_uuid: str,
        archive_uuid: str,
        *,
        sharelink_token: Optional[str] = None,
    ) -> bytes:
        params = {"sharelink_token": sharelink_token} if sharelink_token else None
        response = self.request(
            "GET",
            f"{self.base_url}/2/app/{self.drive_id}/share/{share_uuid}/archive/{archive_uuid}/download",
            params=params,
            allow_redirects=True,
            binary=True,
        )
        return self.handle_binary(response)

    # --- Dropbox ----------------------------------------------------------

    def get_dropbox(self, file_id: Union[str, int]) -> Dict[str, Any]:
        payload = self.json_request(
            "GET",
            self.url(2, f"files/{file_id}/dropbox"),
            params=self.as_params({"with": ["capabilities"]}),
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def create_dropbox(
        self,
        file_id: Union[str, int],
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/dropbox"),
            json=body or {},
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def update_dropbox(
        self,
        file_id: Union[str, int],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "PUT",
            self.url(2, f"files/{file_id}/dropbox"),
            json=body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def delete_dropbox(self, file_id: Union[str, int]) -> bool:
        payload = self.json_request("DELETE", self.url(2, f"files/{file_id}/dropbox"))
        data = self.data(payload)
        return True if data is None else bool(data)

    def invite_dropbox(
        self,
        file_id: Union[str, int],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/dropbox/invite"),
            json=body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    # --- ACL / access -----------------------------------------------------

    def get_access(self, file_id: Union[str, int]) -> Dict[str, Any]:
        payload = self.json_request("GET", self.url(2, f"files/{file_id}/access"))
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def set_access(
        self,
        file_id: Union[str, int],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/access"),
            json=body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def get_access_users(self, file_id: Union[str, int]) -> Any:
        payload = self.json_request("GET", self.url(2, f"files/{file_id}/access/users"))
        return self.data(payload)

    def add_access_users(
        self,
        file_id: Union[str, int],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/access/users"),
            json=body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def update_access_user(
        self,
        file_id: Union[str, int],
        user_id: Union[str, int],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "PUT",
            self.url(2, f"files/{file_id}/access/users/{user_id}"),
            json=body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def remove_access_user(
        self,
        file_id: Union[str, int],
        user_id: Union[str, int],
    ) -> bool:
        payload = self.json_request(
            "DELETE",
            self.url(2, f"files/{file_id}/access/users/{user_id}"),
        )
        data = self.data(payload)
        return True if data is None else bool(data)

    def get_access_teams(self, file_id: Union[str, int]) -> Any:
        payload = self.json_request("GET", self.url(2, f"files/{file_id}/access/teams"))
        return self.data(payload)

    def add_access_teams(
        self,
        file_id: Union[str, int],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/access/teams"),
            json=body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def update_access_team(
        self,
        file_id: Union[str, int],
        team_id: Union[str, int],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "PUT",
            self.url(2, f"files/{file_id}/access/teams/{team_id}"),
            json=body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def remove_access_team(
        self,
        file_id: Union[str, int],
        team_id: Union[str, int],
    ) -> bool:
        payload = self.json_request(
            "DELETE",
            self.url(2, f"files/{file_id}/access/teams/{team_id}"),
        )
        data = self.data(payload)
        return True if data is None else bool(data)

    def get_access_requests(self, file_id: Union[str, int]) -> Any:
        payload = self.json_request(
            "GET",
            self.url(2, f"files/{file_id}/access/requests"),
        )
        return self.data(payload)

    def get_access_request(
        self,
        request_id: Union[str, int],
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "GET",
            self.url(2, f"access/requests/{request_id}"),
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def decline_access_request(
        self,
        request_id: Union[str, int],
        body: Optional[Dict[str, Any]] = None,
    ) -> bool:
        payload = self.json_request(
            "PUT",
            self.url(2, f"access/requests/{request_id}/decline"),
            json=body or {},
        )
        data = self.data(payload)
        return True if data is None else bool(data)

    def grant_access_applications(
        self,
        file_id: Union[str, int],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/access/applications"),
            json=body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def get_access_invitations(self, file_id: Union[str, int]) -> Any:
        payload = self.json_request(
            "GET",
            self.url(2, f"files/{file_id}/access/invitations"),
        )
        return self.data(payload)

    def create_access_request(
        self,
        file_id: Union[str, int],
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/access/requests"),
            json=body or {},
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def check_invitations(
        self,
        file_id: Union[str, int],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/access/check"),
            json=body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def force_invitations(self, file_id: Union[str, int]) -> Dict[str, Any]:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/access/force"),
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def sync_parent_access(self, file_id: Union[str, int]) -> Dict[str, Any]:
        payload = self.json_request(
            "POST",
            self.url(2, f"files/{file_id}/access/sync"),
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    # --- Drive invitations ------------------------------------------------

    def list_invitations(self, **params: Any) -> Any:
        payload = self.json_request(
            "GET",
            self.url(2, "invitations"),
            params=self.as_params(params) or None,
        )
        return self.data(payload)

    def get_invitation(self, invitation_id: Union[str, int]) -> Dict[str, Any]:
        payload = self.json_request("GET", self.url(2, f"invitations/{invitation_id}"))
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def update_invitation(
        self,
        invitation_id: Union[str, int],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = self.json_request(
            "PUT",
            self.url(2, f"invitations/{invitation_id}"),
            json=body,
        )
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}

    def delete_invitation(self, invitation_id: Union[str, int]) -> bool:
        payload = self.json_request("DELETE", self.url(2, f"invitations/{invitation_id}"))
        data = self.data(payload)
        return True if data is None else bool(data)

    def send_invitation(self, body: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.json_request("POST", self.url(2, "invitations"), json=body)
        data = self.data(payload)
        return data if isinstance(data, dict) else {"data": data}
