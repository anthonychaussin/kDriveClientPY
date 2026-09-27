from __future__ import annotations

import pytest

from kdrive_client import KDriveClient, suggest_chunk_size, suggest_direct_threshold
from kdrive_client.upload import ONE_MB


TOKEN = "test-token"
DRIVE_ID = "12345"


def test_suggest_chunk_size_respects_target_and_bounds():
    size = suggest_chunk_size(
        10 * ONE_MB,
        parallelism=4,
        target_seconds=3.0,
        min_chunk_size=ONE_MB,
        max_chunk_size=32 * ONE_MB,
    )
    assert ONE_MB <= size <= 32 * ONE_MB


def test_suggest_direct_threshold_factor():
    assert suggest_direct_threshold(0) == 100 * 1024 * 1024
    low = suggest_direct_threshold(ONE_MB, direct_upload_factor=2.0)
    high = suggest_direct_threshold(ONE_MB, direct_upload_factor=15.0)
    assert low <= high


def test_safe_mode_caps_chunk_and_workers():
    client = KDriveClient(
        TOKEN,
        DRIVE_ID,
        parallelism=8,
        safe_mode=True,
        safe_max_workers=2,
        safe_max_chunk_size=4 * ONE_MB,
        safe_direct_upload_threshold=3 * ONE_MB,
        max_ram_bytes=10 * ONE_MB,
        max_retries=0,
    )
    client.dynamic_chunk_size = 64 * ONE_MB
    client.dynamic_chunk_threshold = 50 * ONE_MB
    assert client.resolve_chunk_size() <= 4 * ONE_MB
    assert client.resolve_chunk_threshold() <= 3 * ONE_MB
    assert client.compute_upload_workers(chunk_size=4 * ONE_MB, total_chunks=20) <= 2


def test_auto_max_workers_and_ram_budget():
    client = KDriveClient(
        TOKEN,
        DRIVE_ID,
        parallelism=8,
        auto_max_workers=True,
        max_ram_bytes=8 * ONE_MB,
        max_retries=0,
    )
    client.measured_speed_bps = 0.5 * ONE_MB  # slow → 1 worker
    assert client.compute_upload_workers(chunk_size=ONE_MB, total_chunks=20) == 1

    client.measured_speed_bps = 20 * ONE_MB
    # RAM: 8 MiB budget / 4 MiB chunk → max 2 workers
    assert client.compute_upload_workers(chunk_size=4 * ONE_MB, total_chunks=20) == 2


def test_invalid_upload_config():
    with pytest.raises(ValueError):
        KDriveClient(TOKEN, DRIVE_ID, target_seconds=0)
    with pytest.raises(ValueError):
        KDriveClient(TOKEN, DRIVE_ID, min_chunk_size=10, max_chunk_size=5)
