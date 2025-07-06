"""Represents a chunk of a KDrive file."""
import dataclasses
import hashlib


@dataclasses.dataclass
class KDriveChunk:
    """Represents a chunk of a KDrive file."""

    index: int
    size: int
    content: bytes

    def get_hash(self):
        """Returns the hash of the file."""
        return hashlib.sha256(self.content).hexdigest()
