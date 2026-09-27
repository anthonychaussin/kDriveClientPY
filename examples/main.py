"""Minimal example using kdrive_client 2.x."""

from __future__ import annotations

import io
import os
from pathlib import Path

from kdrive_client import ConflictMode, KDriveClient, KDriveFile


def _load_env(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


_load_env()

TOKEN = os.environ.get("KDRIVE_TOKEN")
DRIVE_ID = os.environ.get("KDRIVE_DRIVE_ID")
if not TOKEN or not DRIVE_ID:
    raise SystemExit("Set KDRIVE_TOKEN and KDRIVE_DRIVE_ID (see .env.example)")

with KDriveClient(
    TOKEN,
    DRIVE_ID,
    use_auto_chunk_size=True,
    auto_max_workers=True,
    safe_mode=False,
) as client:
    drive, _root = client.bootstrap()
    print("Drive:", drive.name)

    folder = client.ensure_path("Private/examples")
    uploaded = client.upload(
        KDriveFile(
            name="hello.txt",
            directory_id=folder.id,
            content=io.BytesIO(b"Hello from kDriveClient!"),
        ),
        conflict=ConflictMode.RENAME,
    )
    print("Uploaded:", uploaded.id, uploaded.name)

    data = client.download(uploaded.id)
    print("Downloaded bytes:", len(data))
