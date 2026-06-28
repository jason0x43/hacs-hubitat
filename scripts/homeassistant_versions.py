from __future__ import annotations

import calendar
import json
import urllib.request
from datetime import datetime, timezone

PYPI_URL = "https://pypi.org/pypi/homeassistant/json"


def subtract_months(dt: datetime, months: int) -> datetime:
    year = dt.year
    month = dt.month - months
    while month <= 0:
        year -= 1
        month += 12
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def fetch_homeassistant_releases() -> dict[str, list[dict]]:
    with urllib.request.urlopen(PYPI_URL, timeout=15) as response:
        data = json.load(response)
    return data["releases"]


def is_stable_version(version: str) -> bool:
    return bool(version) and all(char.isdigit() or char == "." for char in version)


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def latest_stable_homeassistant_version(
    releases: dict[str, list[dict]] | None = None,
) -> str:
    release_map = releases if releases is not None else fetch_homeassistant_releases()
    candidates = [version for version in release_map if is_stable_version(version)]
    candidates.sort(key=_version_key)
    return candidates[-1]


def six_month_old_homeassistant_version(
    *,
    now: datetime | None = None,
    releases: dict[str, list[dict]] | None = None,
) -> str:
    cutoff = subtract_months(now or datetime.now(timezone.utc), 6)
    release_map = releases if releases is not None else fetch_homeassistant_releases()

    older_candidates: list[str] = []
    for version, files in release_map.items():
        if not is_stable_version(version):
            continue

        upload_times = []
        for file in files:
            timestamp = file.get("upload_time_iso_8601")
            if timestamp:
                upload_times.append(
                    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                )

        if not upload_times or max(upload_times) > cutoff:
            continue

        older_candidates.append(version)

    older_candidates.sort(key=_version_key)
    return older_candidates[-1]
