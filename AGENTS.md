# Repository Guidelines

## Project Structure

- `kdrive_client/` — SDK (mixins: upload, download, files, shares, smart, …)
- `tests/` — unit tests (`pytest`, `responses`)
- `examples/` — runnable samples (`examples/main.py`)
- `.github/workflows/` — CI (`ci.yml`), pylint, PyPI publish

## Development

```bash
pip install -e ".[dev]"
pytest -m "not integration"
```

Live tests: set `KDRIVE_TOKEN` / `KDRIVE_DRIVE_ID` (see `.env.example`), then `pytest -m integration`.

## Upload tuning

Optional constructor knobs on `KDriveClient`:

- `use_auto_chunk_size` / `auto_max_workers` / `safe_mode`
- `target_seconds`, `min_chunk_size`, `max_chunk_size`, `direct_upload_factor`
- `safe_max_workers`, `safe_max_chunk_size`, `safe_direct_upload_threshold`
- `max_ram_bytes` (caps concurrent chunk buffers)

## Security

Do not commit tokens. Redact `Authorization` headers in shared logs.
