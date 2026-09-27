from __future__ import annotations

from typing import BinaryIO, Optional, Union


class KDriveFile:
    """Input payload for upload endpoints."""

    def __init__(
        self,
        name: str,
        content: BinaryIO,
        *,
        directory_path: Optional[str] = None,
        directory_id: Optional[int] = None,
        file_id: Optional[int] = None,
        total_size: Optional[int] = None,
        created_at: Optional[int] = None,
        last_modified_at: Optional[int] = None,
        symbolic_link: Optional[Union[bool, str]] = None,
    ):
        if directory_path is None and directory_id is None and file_id is None:
            raise ValueError("Provide directory_path, directory_id, or file_id")

        self.name = name.replace("/", ":")
        self.content = content
        self.directory_path = directory_path
        self.directory_id = directory_id
        self.file_id = file_id
        self.created_at = created_at
        self.last_modified_at = last_modified_at
        self.symbolic_link = symbolic_link

        if total_size is not None:
            self.total_size = total_size
        elif hasattr(content, "getbuffer"):
            self.total_size = len(content.getbuffer())
        else:
            pos = content.tell()
            content.seek(0, 2)
            self.total_size = content.tell() - pos
            content.seek(pos)

    def upload_timing_params(self) -> dict:
        """Query/body fields for created_at / last_modified_at / symbolic_link."""
        params = {}
        if self.created_at is not None:
            params["created_at"] = int(self.created_at)
        if self.last_modified_at is not None:
            params["last_modified_at"] = int(self.last_modified_at)
        if self.symbolic_link is not None:
            params["symbolic_link"] = self.symbolic_link
        return params
