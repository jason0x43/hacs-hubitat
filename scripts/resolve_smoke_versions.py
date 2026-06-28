#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json

from homeassistant_versions import (
    latest_stable_homeassistant_version,
    six_month_old_homeassistant_version,
)


def smoke_matrix() -> dict[str, list[dict[str, str]]]:
    return {
        "include": [
            {
                "label": "current",
                "ha_version": latest_stable_homeassistant_version(),
            },
            {
                "label": "6 months ago",
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
