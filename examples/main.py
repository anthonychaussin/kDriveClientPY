"""Module to test client"""

import os

from kdrive_client.kdrive_client import KDriveClient
from kdrive_client.kdrive_file import KDriveFile

TOKEN = "TOKEN"
DRIVE_ID = 1234

client = KDriveClient(TOKEN, DRIVE_ID)

SMALL_PATH = "test_small.txt"
with open(SMALL_PATH, "w", encoding="utf-8") as f:
    f.write("Hello from kDriveClient!")

LARGE_PATH = "test_large.bin"
if not os.path.exists(LARGE_PATH):
    with open(LARGE_PATH, "wb") as f:
        f.write(os.urandom(10 * 1024 * 1024))  # 10 Mo

small_file = KDriveFile(SMALL_PATH)

small_response = client.upload(small_file, "/Private", None, "rename")
print("✔️ Small file uploaded. ID:", small_response["id"])

large_file = KDriveFile(LARGE_PATH)

large_response = client.upload(large_file, "/Private", None, "rename")
print("✔️ Large file uploaded. ID:", large_response["id"])

downloaded_data = client.download(small_response["id"])
with open("downloaded_small.txt", "wb") as f:
    f.write(downloaded_data)
print("⬇️ Small file downloaded as downloaded_small.txt")

with open("downloaded_large.bin", "wb") as f:
    client.download_to(large_response["id"], f)
print("⬇️ Large file downloaded as downloaded_large.bin")
