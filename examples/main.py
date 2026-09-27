"""Minimal example using kdrive_client 2.x."""

from __future__ import annotations

import io
import os

from kdrive_client import ConflictMode, KDriveClient, KDriveFile

TOKEN = os.environ["KDRIVE_TOKEN"]
DRIVE_ID = os.environ["KDRIVE_DRIVE_ID"]

with KDriveClient(TOKEN, DRIVE_ID) as client:
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
