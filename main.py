from kdrive_client import (
    ConflictMode,
    KDriveClient,
    KDriveFile,
    Order,
    OrderBy,
)
import io

client = KDriveClient("your_token", "your_drive_id")

# List root
listing = client.list_files(1, limit=50, order_by=OrderBy.NAME, order=Order.ASC)
for entry in listing:
    print(entry.id, entry.type, entry.name)

# Create folder
folder = client.create_directory(1, "docs")

# Direct / auto upload
content = io.BytesIO(b"Hello World!")
file = KDriveFile(name="hello.txt", directory_id=folder.id, content=content)
uploaded = client.upload(file, conflict=ConflictMode.RENAME)
print(uploaded)

# Chunked upload with progress
def progress(pct):
    print(f"Uploaded: {pct:.2f}%")

client.progress_callback = progress
content = io.BytesIO(b"A" * 2 * 1024 * 1024)  # 2 MB
file = KDriveFile(name="big.bin", directory_path="/docs", content=content)
response = client.upload_chunked(file)
print(response)

# Search
results = client.search(query="hello", directory_id=folder.id)
print(len(results), results.has_more)

# Download
data = client.download(uploaded.id)
with open("output.bin", "wb") as f:
    f.write(data)
