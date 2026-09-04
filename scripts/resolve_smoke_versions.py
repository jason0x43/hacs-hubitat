#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json

if __package__:
    from scripts.homeassistant_versions import (
        fetch_homeassistant_releases,
        latest_stable_homeassistant_version,
        next_beta_homeassistant_version,
        six_month_old_homeassistant_version,
    )
else:
    from homeassistant_versions import (
        fetch_homeassistant_releases,
        latest_stable_homeassistant_version,
        next_beta_homeassistant_version,
        six_month_old_homeassistant_version,
    )


def smoke_matrix() -> dict[str, list[dict[str, str]]]:
    releases = fetch_homeassistant_releases()
    current_version = latest_stable_homeassistant_version(releases)
    next_beta_version = next_beta_homeassistant_version(current_version, releases)
    include = [
        {
            "label": "current",
            "ha_version": current_version,
        },
        {
            "label": "6 months ago",
            "ha_version": six_month_old_homeassistant_version(releases=releases),
        },
    ]

    if next_beta_version:
        include.append(
            {
                "label": "next (latest beta)",
                "ha_version": next_beta_version,
            }
        )

    return {"include": include}


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
