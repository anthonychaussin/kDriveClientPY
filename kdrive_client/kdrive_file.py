"""Represents a file to upload to kDrive."""

import hashlib
import os

from kdrive_client.kdrive_chunk import KDriveChunk


class KDriveFile:
    """Represents a file to upload to kDrive."""

    def __init__(self, path: str, symbolic_link: str = None):
        self.chunks = []
        self.path = path
        self.total_size: int = os.path.getsize(self.path)
        self.symbolic_link = symbolic_link

    def prepare(self, chunk_size: int):
        """Prepares the file to upload to kDrive."""

        chunk_hashes = []
        with open(self.path, "rb") as fh:
            while True:
                chunk = fh.read(chunk_size)
                if not chunk:
                    break

                drive_chunk = KDriveChunk(
                    len(self.chunks) + 1,
                    len(chunk),
                    chunk
                )
                self.chunks.append(drive_chunk)
                chunk_hashes.append(drive_chunk.get_hash())

    def get_total_hash(self):
        """Returns the hash of the file."""
        chunk_hashes = []
        for chunk in self.chunks:
            chunk_hashes.append(chunk.get_hash())

        return hashlib.sha256(''.join(chunk_hashes).encode('utf-8')).hexdigest()

    def file_params(self, directory_id: int = None, directory_path: str = None) -> dict:
        """Returns the params needed to upload the file."""

        stat = os.stat(self.path)

        params = {
            "file_name": os.path.basename(self.path).replace("/", ":"),
            "created_date": str(int(stat.st_birthtime)),
            "last_modified_at": str(int(stat.st_mtime))
        }
        if directory_id:
            params["directory_id"] = str(directory_id)
        elif directory_path:
            params["directory_path"] = directory_path

        if self.symbolic_link:
            params["with"] = self.symbolic_link
        return params
