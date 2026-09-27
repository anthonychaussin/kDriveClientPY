# kdrive_client

SDK Python pour l'API Infomaniak kDrive — aligné sur l'architecture du SDK C# [DriveClient](https://github.com/anthonychaussin/DriveClient).

- Pipeline HTTP unique + **rate limit 60 req/min** + retry 429/5xx
- Mixins domaine : upload, download, files, trash, shares, comments, categories, drive, smart
- Upload direct / chunké parallèle (SHA-256 ou XXH3)
- Queries typées (`ListQuery`, `SearchQuery`, `ItemIncludes`)
- Helpers smart (chemins, arborescence local↔cloud, bootstrap, pagination, wake)

## Installation

```bash
pip install kdrive_client
# optionnel : hash XXH3 plus rapide
pip install kdrive_client[xxh]
# optionnel : prepare async / httpx
pip install kdrive_client[async]
```

Depuis les sources :

```bash
cd kDriveClient
pip install -e ".[dev]"
```

Token API : [Manager Infomaniak](https://manager.infomaniak.com/v3/ng/accounts/token/list) (scope `drive`).

Publication PyPI : package `kdrive_client` (PEP 561 / `py.typed`).

## Usage

```python
from kdrive_client import (
    KDriveClient,
    KDriveFile,
    ConflictMode,
    ListQuery,
    ItemIncludes,
)
import io

with KDriveClient("your_token", "your_drive_id") as client:
    drive, root = client.bootstrap()
    print(drive.name, len(root))

    folder = client.create_folder(1, "docs")  # alias de create_directory
    content = io.BytesIO(b"Hello")
    uploaded = client.upload(
        KDriveFile(
            name="hello.txt",
            directory_id=folder.id,
            content=content,
            created_at=1700000000,
            last_modified_at=1700000001,
        ),
        conflict=ConflictMode.RENAME,
    )

    page = client.list_files(1, query=ListQuery(limit=50, includes=ItemIncludes.PATH))
    client.download_progress_callback = print  # % 0–100
    client.download_to_path(uploaded.id, "out.bin")
    link = client.create_share_link(uploaded.id, right="public", can_download=True)
```

### Async

```python
import asyncio
from kdrive_client import AsyncKDriveClient, KDriveFile
import io

async def main():
    async with AsyncKDriveClient("your_token", "your_drive_id") as client:
        page = await client.list_files(1)
        # client.cancel() pour interrompre un upload long
        await client.upload(
            KDriveFile(name="a.txt", directory_id=1, content=io.BytesIO(b"x"))
        )

asyncio.run(main())
```

## Quelle API appeler ?

| Objectif | Préférer | Notes |
|---------|----------|-------|
| Fichiers au quotidien | `get_item`, `list_files`, `create_folder`, `trash`, `undo` | Alias métier style C# |
| Chemins / arborescence | `resolve_path`, `ensure_path`, `upload_tree`, `download_folder` | Smart DX 2.3 |
| Partage / commentaires / tags | `create_share_link`, `create_comment`, `add_category` | v2 pour link/comments/categories |
| Pagination / recherche | `list_all_files` (= `enumerate_files`), `search_all`, `bootstrap` | Smart helpers |
| Upload | `upload` / `upload_from_path`, `upload_chunked` | Batch : `start_upload_session_batch` |
| Download | `download` / `download_to_path` / `download_folder` | Password, `as=`, temporary_url |
| Admin | `wake`, users, stats, imports, preferences | Module drive |

Préférer **v3** quand v2 et v3 coexistent. v2 conservé pour favoris, share links, commentaires, catégories, restore trash.

## Architecture

```
kdrive_client/
  http.py          # HttpPipeline + FixedWindowRateLimiter
  client.py        # façade sync (mixins)
  async_client.py  # AsyncKDriveClient (asyncio.to_thread + cancel)
  queries.py       # ListQuery / SearchQuery / ItemIncludes
  upload.py … smart.py
  models/
  py.typed
```

User-Agent : `kdrive_client/2.3.1`. Logging : logger `kdrive_client`.

### Smart DX 2.3

- Chemins : `resolve_path`, `ensure_path` (multi-niveaux)
- Arborescence : `upload_from_path`, `upload_tree`, `download_folder` (one-way)
- Bootstrap multi-drive : `account_id` / `preferred_drive_id` + `rebind_drive_id`
- `ensure_drive_awake` throttlé (2 min) + auto-wake sur `enumerate_*`
- Agrégateurs : `search_all`, `list_all_invitations`, `list_trash_children_all`, `list_versions_all`, activités
- `copy_between_drives(wait=True)`, `find_trash_item` ranking, `wait_for_archive`
- `list_all_comments` / `users` / `categories` typés
- Upload tuning (2.3.1) : `safe_mode`, `auto_max_workers`, `max_ram_bytes`, `target_seconds`, …

### Polish 2.2

- Métadonnées upload : `created_at` / `last_modified_at` / `symbolic_link`
- Seuil direct dynamique (`suggest_direct_threshold` / bande passante)
- Progress download (`download_progress_callback`)
- `AsyncKDriveClient` + `cancel()` / `UploadCancelled`
- Dataclasses `Comment`, `Invitation`, `ActivityReport` + `py.typed`
- CI : job intégration optionnel (`pytest -m integration`)

### Polish 2.1

- `upload_batch`, auto chunk size (`use_auto_chunk_size=True`)
- `build_and_download_archive`, archives de share-link
- Smart : `search_trash_all`, `find_trash_item`, `wait_for_import_complete`, …
- Modèles légers : `AccessUser`, `Category`, `ExternalImport`

## Domaines couverts

| Mixin | Exemples |
|-------|----------|
| Upload | `upload`, `upload_chunked`, `cancel_upload_session`, batch |
| Download | `download*`, preview, thumbnail, archive, temporary_url |
| Files | list/search/versions/archives/convert/team/exists/activities |
| Trash | list/restore/purge/empty/count/children |
| Favorites | list/favorite/unfavorite |
| Shares | share links, dropbox, ACL users/teams, invitations |
| Comments | CRUD + like/unlike |
| Categories | CRUD, rights, tag/untag, AI feedback |
| Drive | info, settings, users, wake, activities, stats, imports |
| Smart | bootstrap, enumerate_*, ensure_drive_awake, wait_for_async_result |

## Versions API

| Domaine | Version |
|---------|---------|
| Upload, list, search, copy, move, create dir | v3 |
| Download, rename, trash, cancel, favoris, links, comments, categories | v2 |
| Infos drive | v2 |
| Wake / activities v3 | v3 |

Doc officielle : https://developer.infomaniak.com/docs/api

## Tests

```bash
pip install -e ".[dev]"
pytest -m "not integration"
# live (nécessite KDRIVE_TOKEN et KDRIVE_DRIVE_ID) :
pytest -m integration
```

## License

MIT
