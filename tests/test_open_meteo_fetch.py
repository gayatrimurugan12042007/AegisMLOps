"""Unit tests for acquisition validation and immutable caching."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta

import pytest

from scripts import fetch_open_meteo


def make_payload(start: date, hours: int = 24) -> dict[str, object]:
    """Build a small valid hourly response fixture."""
    times = [
        (datetime.combine(start, datetime.min.time()) + timedelta(hours=i)).isoformat()
        for i in range(hours)
    ]
    hourly = {"time": times, "temperature_2m": [25.0] * hours}
    return {
        "latitude": 13.08,
        "longitude": 80.27,
        "timezone": "GMT",
        "utc_offset_seconds": 0,
        "hourly": hourly,
        "hourly_units": {"temperature_2m": "°C"},
    }


def test_validate_payload_reports_rows_units_and_nulls() -> None:
    payload = make_payload(date(2024, 1, 1))

    result = fetch_open_meteo.validate_payload(
        payload, date(2024, 1, 1), date(2024, 1, 1), ["temperature_2m"]
    )

    assert result["row_count"] == 24
    assert result["units"] == {"temperature_2m": "°C"}
    assert result["null_counts"] == {"temperature_2m": 0}


def test_validate_payload_rejects_missing_values_array() -> None:
    payload = make_payload(date(2024, 1, 1))
    payload["hourly"].pop("temperature_2m")  # type: ignore[union-attr]

    with pytest.raises(ValueError, match="missing or has a different array length"):
        fetch_open_meteo.validate_payload(
            payload, date(2024, 1, 1), date(2024, 1, 1), ["temperature_2m"]
        )


def test_validate_payload_rejects_timestamp_gap() -> None:
    payload = make_payload(date(2024, 1, 1))
    times = payload["hourly"]["time"]  # type: ignore[index]
    times[2:] = [
        (datetime.fromisoformat(value) + timedelta(hours=1)).isoformat()
        for value in times[2:]
    ]

    with pytest.raises(ValueError, match="not continuous"):
        fetch_open_meteo.validate_payload(
            payload, date(2024, 1, 1), date(2024, 1, 1), ["temperature_2m"]
        )


def test_estimated_billing_units_follow_10_variable_14_day_basis() -> None:
    assert (
        fetch_open_meteo.estimate_billable_calls(
            10, date(2024, 1, 1), date(2024, 1, 14)
        )
        == 1.0
    )
    assert (
        fetch_open_meteo.estimate_billable_calls(
            15, date(2024, 1, 1), date(2024, 1, 14)
        )
        == 1.5
    )
    assert (
        fetch_open_meteo.estimate_billable_calls(
            10, date(2024, 1, 1), date(2024, 1, 28)
        )
        == 2.0
    )


def test_saved_raw_response_is_cached_and_checksum_verified(
    tmp_path, monkeypatch
) -> None:
    body = json.dumps(make_payload(date(2024, 1, 1))).encode()
    calls = 0

    def fake_request(url: str) -> tuple[bytes, int, int]:
        nonlocal calls
        calls += 1
        return body, 200, 1

    monkeypatch.setattr(fetch_open_meteo, "request_bytes", fake_request)
    first = fetch_open_meteo.save_immutable_chunk(
        tmp_path,
        "historical-weather",
        "era5",
        date(2024, 1, 1),
        date(2024, 1, 1),
        ["temperature_2m"],
        "https://example.invalid/archive",
        0,
    )
    second = fetch_open_meteo.save_immutable_chunk(
        tmp_path,
        "historical-weather",
        "era5",
        date(2024, 1, 1),
        date(2024, 1, 1),
        ["temperature_2m"],
        "https://example.invalid/archive",
        0,
    )

    assert calls == 1
    assert first["sha256"] == hashlib.sha256(body).hexdigest()
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert second["runtime_http_requests"] == 0
