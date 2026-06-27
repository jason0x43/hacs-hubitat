#!/usr/bin/env python3

from __future__ import annotations

import argparse
import calendar
import json
import subprocess
import urllib.request
from datetime import datetime, timezone


def subtract_months(dt: datetime, months: int) -> datetime:
    year = dt.year
    month = dt.month - months
    while month <= 0:
        year -= 1
        month += 12
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def current_homeassistant_version() -> str:
    output = subprocess.run(
        ["uv", "tree", "--package", "homeassistant", "--frozen", "--depth", "0"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return output.split()[1].removeprefix("v")


def six_month_old_homeassistant_version() -> str:
    cutoff = subtract_months(datetime.now(timezone.utc), 6)

    with urllib.request.urlopen("https://pypi.org/pypi/homeassistant/json") as response:
        data = json.load(response)

    older_candidates: list[tuple[tuple[int, ...], str]] = []
    for version, files in data["releases"].items():
        if not version or any(not (char.isdigit() or char == ".") for char in version):
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

        older_candidates.append(
            (tuple(int(part) for part in version.split(".")), version)
        )

    older_candidates.sort()
    return older_candidates[-1][1]


def smoke_matrix() -> dict[str, list[dict[str, str]]]:
    return {
        "include": [
            {
                "label": "current",
                "ha_version": current_homeassistant_version(),
            },
            {
                "label": "six_months_ago",
                "ha_version": six_month_old_homeassistant_version(),
            },
        ]
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve Home Assistant versions for smoke-test CI."
    )
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="Print in GitHub Actions output format as matrix=<json>.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    matrix_json = json.dumps(smoke_matrix(), separators=(",", ":"))
    if args.github_output:
        print(f"matrix={matrix_json}")
    else:
        print(matrix_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
