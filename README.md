# 📦 kDriveClientPY

Python SDK for the [Infomaniak kDrive API](https://www.infomaniak.com/en/support/faq/admin2/kdrive).

> ⚠️ This library is not officially maintained by Infomaniak but made with ❤️ by Anthony.

---

## ✅ Features

- Upload small and large files (automatic chunking)
- Download files as stream or directly to disk
- Error handling with parsed API errors
- Rate limiter (60 requests/minute)
- Automatic speed test to decide best upload strategy

---

## 💡 Installation

```bash
pip install kdrive_client
```

---

## 🚀 Quick Start

```python
from kdrive_client import kdrive_client, kdrive_file

client = KDriveClient(token="your-token", drive_id=123456)

# Upload
file = KDriveFile("example.txt", directory_path="/Private")
response = client.upload(file)
print("Uploaded file ID:", response["id"])

# Download to file
with open("downloaded.txt", "wb") as f:
    client.download_to(file_id=response["id"], dest=f)

# Or get raw bytes
raw_data = client.download(response["id"])
```

---

## 🔒 License

MIT License — use freely, contribute with joy 😄

---

## 📫 Author

Made by Anthony Chaussin — [GitHub](https://github.com/anthonychaussin)
