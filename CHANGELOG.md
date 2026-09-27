# Changelog

## 2.3.0

Smart DX — workflows chemins / arborescence.

### Chemins et fichiers
- `resolve_path` / `ensure_path` (création multi-niveaux)
- `upload_from_path`, `upload_tree`, `download_folder` (miroir one-way)
- Pas de sync bidirectionnel (volontairement hors scope)

### Alignement C# smart
- `bootstrap(account_id=..., preferred_drive_id=...)` + `rebind_drive_id`
- `ensure_drive_awake` throttlé (120 s) + auto-wake sur énumérations longues
- `search_all`, `list_all_invitations`, `list_trash_children_all`, `list_versions_all`
- `list_file_activities_all` / `list_drive_activities_all`
- `copy_between_drives(..., wait=True)` → `wait_for_import_complete`
- `find_trash_item` avec ranking name/path
- `wait_for_archive` ; `build_and_download_archive` via `wait_for_async_result`

### Typage
- `list_all_comments` / `list_all_users` / `list_all_categories` / `list_all_invitations` → dataclasses

## 2.2.0

Polish production Python (post-parité API).

### Upload / download
- `KDriveFile.created_at` / `last_modified_at` / `symbolic_link` transmis en query
- Seuil upload direct dynamique (`suggest_direct_threshold`, `dynamic_chunk_threshold`)
- `download_progress_callback` (% 0–100) sur `download_iter` / `download_to_path`
- Annulation upload via `cancel_check` / `UploadCancelled`

### Async
- `AsyncKDriveClient` (`asyncio.to_thread`) + `cancel()` / `reset_cancel()`
- Extra optionnel `[async]` (httpx)

### Typage / DX
- Dataclasses `Comment`, `Invitation`, `ActivityReport`
- Marqueur PEP 561 `py.typed`
- Métadonnées PyPI enrichies (classifiers, keywords, URLs)
- CI : tests unitaires + job `integration` optionnel (`pytest -m integration`)

## 2.1.0

Polish résiduel vs DriveClient C#.

### Upload
- `upload_batch` (API batch + fallback parallèle)
- `cancel_upload_sessions_batch`
- `use_auto_chunk_size` / `measure_upload_bandwidth` / `suggest_chunk_size`

### Download / archives
- `build_and_download_archive`, `get_archive_status`
- `create_share_link_archive` / `download_share_link_archive`
- Options `use_temporary_url` et `expected_hash` sur download

### Smart
- `*_all` / enumerate dropboxes, links, search trash, comments, users
- `find_trash_item`, `restore_latest_version_to`
- `wait_for_async_result` générique, `wait_for_import_complete`, `copy_between_drives`

### Niche + modèles
- `undo` multi-ids, `update_version_v2`, `remove_all_categories`
- ACL : decline request, grant applications, access invitations
- Stats typées + `clear_imports_history` / `list_oauth_import_drives`
- Dataclasses `AccessUser`, `Category`, `ExternalImport`

### DX
- CI GitHub Actions (pytest)
- Version 2.1.0

## 2.0.0

Alignement architectural avec le SDK C# DriveClient.

### Architecture
- `HttpPipeline` + `FixedWindowRateLimiter` (60 req/min)
- Client découpé en mixins domaine (upload, download, files, trash, favorites, shares, comments, categories, drive, smart)
- Queries typées : `ListQuery`, `SearchQuery`, `ItemIncludes`
- User-Agent `kdrive_client/{version}`, logging stdlib
- Alias métier : `get_item`, `create_folder`, `undo`, `add_favorite`, …

### Couverture API (parité C#)
- Files : largest, links, most_versions, versions v2/v3, archives, convert, team directory, exists, hash, sizes, activities, search spécialisées
- Download : preview, thumbnail, version, archive, temporary_url, password
- Shares : ACL users/teams, dropbox, invitations, shared_with_me
- Comments + Categories complets
- Drive admin : settings, users, wake, activities/reports, statistics, imports, preferences, copy-to-drive
- Smart helpers : bootstrap, enumerate_*, get_or_create_folder, ensure_drive_awake, wait_for_async_result
- Upload : hash XXH3 optionnel, cancel by path, batch start/finish

### Breaking
- Version majeure : organisation interne en modules (API publique historique conservée)
- Package version `2.0.0`

## 1.2.0

Robustesse HTTP, trash/favoris/sharelinks de base, tests unitaires.

## 1.1.0

Upload direct/chunked, download, list, search, rename, move, copy, trash.
