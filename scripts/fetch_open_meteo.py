"""Fetch and validate immutable Open-Meteo hourly JSON chunks."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import ssl
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi

COORDINATES = (13.0827, 80.2707)
HOURLY_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "pressure_msl",
    "surface_pressure",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "precipitation",
    "shortwave_radiation",
)
ENDPOINTS = {
    "historical-weather": "https://archive-api.open-meteo.com/v1/archive",
    "historical-forecast": "https://historical-forecast-api.open-meteo.com/v1/forecast",
    "previous-runs": "https://previous-runs-api.open-meteo.com/v1/forecast",
    "forecast": "https://api.open-meteo.com/v1/forecast",
}
MAX_ATTEMPTS = 5
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
LOG = logging.getLogger("aegis.open_meteo")


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=ENDPOINTS, default="historical-weather")
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    parser.add_argument(
        "--models", help="Open-Meteo model identifier or comma-separated list"
    )
    parser.add_argument("--hourly", default=",".join(HOURLY_VARIABLES))
    parser.add_argument("--output", type=Path, default=Path("data/raw/open_meteo"))
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument(
        "--smoke-test", action="store_true", help="Fetch a recent one-week UTC interval"
    )
    return parser


def parse_date_range(args: argparse.Namespace) -> tuple[date, date]:
    """Return validated dates; smoke mode chooses a recent ERA5-ready week."""
    if args.smoke_test:
        end = datetime.now(timezone.utc).date() - timedelta(days=8)
        start = end - timedelta(days=6)
    else:
        if args.start is None or args.end is None:
            raise ValueError(
                "--start and --end are required unless --smoke-test is used"
            )
        start, end = args.start, args.end
    if end < start:
        raise ValueError("end date must be on or after start date")
    return start, end


def estimate_billable_calls(variable_count: int, start: date, end: date) -> float:
    """Estimate Open-Meteo call units using its 10-variable / 14-day basis."""
    days = (end - start).days + 1
    return max(1.0, variable_count / 10.0) * max(1.0, days / 14.0)


def make_request_url(
    source: str, start: date, end: date, variables: list[str], model: str | None
) -> str:
    """Build a stable request URL for a UTC hourly interval."""
    query: dict[str, str] = {
        "latitude": str(COORDINATES[0]),
        "longitude": str(COORDINATES[1]),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(variables),
        "timezone": "UTC",
        "temperature_unit": "celsius",
        "wind_speed_unit": "ms",
        "precipitation_unit": "mm",
    }
    if model:
        query["models"] = model
    return f"{ENDPOINTS[source]}?{urlencode(query)}"


def retry_after_seconds(headers: Any, attempt: int) -> float:
    """Return the server's Retry-After delay or capped exponential backoff."""
    raw = headers.get("Retry-After") if headers is not None else None
    try:
        return min(60.0, max(1.0, float(raw))) if raw else min(60.0, 2.0**attempt)
    except (TypeError, ValueError):
        return min(60.0, 2.0**attempt)


def request_bytes(url: str) -> tuple[bytes, int, int]:
    """Fetch response bytes with bounded retries for rate limits and server errors."""
    request = Request(
        url, headers={"User-Agent": "AegisMLOps-research/0.1 (non-commercial)"}
    )
    for attempt in range(MAX_ATTEMPTS):
        try:
            tls_context = ssl.create_default_context(cafile=certifi.where())
            with urlopen(request, timeout=30, context=tls_context) as response:
                status = response.status
                body = response.read()
            if status in RETRYABLE_STATUS:
                if attempt == MAX_ATTEMPTS - 1:
                    raise RuntimeError(
                        f"Open-Meteo returned HTTP {status} after {MAX_ATTEMPTS} attempts"
                    )
                time.sleep(retry_after_seconds({}, attempt))
                continue
            if status < 200 or status >= 300:
                raise RuntimeError(f"Open-Meteo returned HTTP {status}")
            return body, status, attempt + 1
        except HTTPError as error:
            if error.code not in RETRYABLE_STATUS or attempt == MAX_ATTEMPTS - 1:
                raise RuntimeError(
                    f"Open-Meteo returned HTTP {error.code}: {error.reason}"
                ) from error
            time.sleep(retry_after_seconds(error.headers, attempt))
        except URLError as error:
            if attempt == MAX_ATTEMPTS - 1:
                raise RuntimeError(
                    f"Open-Meteo request failed after {MAX_ATTEMPTS} attempts: {error.reason}"
                ) from error
            time.sleep(min(60.0, 2.0**attempt))
    raise AssertionError("retry loop exited unexpectedly")


def validate_payload(
    payload: Any, start: date, end: date, variables: list[str]
) -> dict[str, Any]:
    """Validate JSON shape, array lengths, timestamps, units, and null counts."""
    if not isinstance(payload, dict) or payload.get("error"):
        raise ValueError(f"API returned an error object: {payload!r}")
    if payload.get("utc_offset_seconds") != 0:
        raise ValueError("response timestamps are not in UTC")
    if not isinstance(payload.get("timezone"), str) or not payload.get("timezone"):
        raise ValueError("response timezone metadata is missing")
    hourly = payload.get("hourly")
    units = payload.get("hourly_units")
    if not isinstance(hourly, dict) or not isinstance(units, dict):
        raise ValueError("response is missing hourly data or hourly_units")
    times = hourly.get("time")
    if not isinstance(times, list):
        raise ValueError("hourly.time is missing or is not an array")
    expected = ((end - start).days + 1) * 24
    if len(times) != expected:
        raise ValueError(f"expected {expected} hourly rows, received {len(times)}")
    parsed_times = [
        datetime.fromisoformat(value.replace("Z", "+00:00")) for value in times
    ]
    if len(set(parsed_times)) != len(parsed_times):
        raise ValueError("timestamps contain duplicates")
    if any(
        (right - left) != timedelta(hours=1)
        for left, right in zip(parsed_times, parsed_times[1:])
    ):
        raise ValueError("timestamps are not continuous at one-hour intervals")
    expected_first = datetime.combine(start, datetime.min.time())
    expected_last = datetime.combine(end, datetime.min.time()) + timedelta(hours=23)
    if (
        parsed_times[0].replace(tzinfo=None) != expected_first
        or parsed_times[-1].replace(tzinfo=None) != expected_last
    ):
        raise ValueError("timestamps do not cover the requested UTC date range")
    null_counts: dict[str, int] = {}
    for name in variables:
        values = hourly.get(name)
        if not isinstance(values, list) or len(values) != len(times):
            raise ValueError(f"{name} is missing or has a different array length")
        if (
            name not in units
            or not isinstance(units[name], str)
            or not units[name].strip()
        ):
            raise ValueError(f"unit metadata missing for {name}")
        null_counts[name] = sum(value is None for value in values)
        for value in values:
            if value is not None and (
                not isinstance(value, (int, float)) or not math.isfinite(value)
            ):
                raise ValueError(f"{name} contains a non-finite or non-numeric value")
    return {
        "row_count": len(times),
        "first_timestamp": times[0],
        "last_timestamp": times[-1],
        "timezone": payload["timezone"],
        "utc_offset_seconds": payload["utc_offset_seconds"],
        "grid_latitude": payload.get("latitude"),
        "grid_longitude": payload.get("longitude"),
        "grid_elevation_m": payload.get("elevation"),
        "units": {name: units[name] for name in variables},
        "null_counts": null_counts,
    }


def save_immutable_chunk(
    output: Path,
    source: str,
    model: str | None,
    start: date,
    end: date,
    variables: list[str],
    url: str,
    sleep_seconds: float,
) -> dict[str, Any]:
    """Reuse a validated cache entry or save one immutable response and manifest."""
    identity = json.dumps(
        {
            "source": source,
            "model": model,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "hourly": variables,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    key = hashlib.sha256(identity).hexdigest()[:16]
    directory = output / source
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"{source}_{start.isoformat()}_{end.isoformat()}_{key}"
    raw_path = directory / f"{stem}.json"
    manifest_path = directory / f"{stem}.manifest.json"
    if raw_path.exists() and manifest_path.exists():
        body = raw_path.read_bytes()
        manifest = json.loads(manifest_path.read_text())
        if hashlib.sha256(body).hexdigest() != manifest.get("sha256"):
            raise ValueError(f"cached raw response checksum mismatch: {raw_path}")
        details = validate_payload(json.loads(body), start, end, variables)
        LOG.info("cache hit %s", raw_path)
        return {
            **manifest,
            "validation": details,
            "cache_hit": True,
            "runtime_http_requests": 0,
        }
    if raw_path.exists() or manifest_path.exists():
        raise FileExistsError(
            f"incomplete cache pair exists; refusing overwrite: {raw_path}"
        )

    if sleep_seconds > 0:
        time.sleep(sleep_seconds)
    body, status, attempts = request_bytes(url)
    payload = json.loads(body)
    details = validate_payload(payload, start, end, variables)
    digest = hashlib.sha256(body).hexdigest()
    manifest = {
        "schema_version": 1,
        "source": source,
        "model": model or "best_match_or_api_default",
        "request_url": url,
        "requested_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_latitude": COORDINATES[0],
        "requested_longitude": COORDINATES[1],
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly_variables": variables,
        "http_status": status,
        "http_requests": attempts,
        "estimated_billable_call_units": (
            estimate_billable_calls(len(variables), start, end) * attempts
        ),
        "raw_file": raw_path.name,
        "raw_bytes": len(body),
        "sha256": digest,
        "validation": details,
    }
    with raw_path.open("xb") as raw_file:
        raw_file.write(body)
    with manifest_path.open("x", encoding="utf-8") as manifest_file:
        manifest_file.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    LOG.info("saved %s (%d rows, %s sha256)", raw_path, details["row_count"], digest)
    return {
        **manifest,
        "cache_hit": False,
        "runtime_http_requests": attempts,
    }


def main() -> None:
    """Fetch and report one requested data interval."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    args = build_parser().parse_args()
    start, end = parse_date_range(args)
    variables = [part.strip() for part in args.hourly.split(",") if part.strip()]
    if len(variables) != len(set(variables)) or not variables:
        raise SystemExit("--hourly must contain unique variable names")
    chunks: list[tuple[date, date]] = []
    chunk_start = start
    while chunk_start <= end:
        chunk_end = min(end, chunk_start + timedelta(days=13))
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end + timedelta(days=1)
    results = []
    for chunk_start, chunk_end in chunks:
        url = make_request_url(
            args.source, chunk_start, chunk_end, variables, args.models
        )
        results.append(
            save_immutable_chunk(
                args.output,
                args.source,
                args.models,
                chunk_start,
                chunk_end,
                variables,
                url,
                args.sleep_seconds,
            )
        )
    report = {
        "source": args.source,
        "model": args.models or "best_match_or_api_default",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly_variables": variables,
        "chunk_count": len(results),
        "http_requests_this_run": sum(
            result["runtime_http_requests"] for result in results
        ),
        "estimated_billable_call_units_this_run": sum(
            result["estimated_billable_call_units"]
            for result in results
            if not result["cache_hit"]
        ),
        "chunks": results,
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
