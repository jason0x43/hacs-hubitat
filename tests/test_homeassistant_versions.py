from datetime import datetime, timezone

from scripts.homeassistant_versions import (
    latest_stable_homeassistant_version,
    six_month_old_homeassistant_version,
)


def test_latest_stable_homeassistant_version_ignores_prereleases() -> None:
    releases: dict[str, list[dict]] = {
        "2026.6.4": [],
        "2026.7.0b0": [],
        "2026.7.0.dev0": [],
        "2026.5.9": [],
    }

    assert latest_stable_homeassistant_version(releases) == "2026.6.4"


def test_six_month_old_homeassistant_version_uses_latest_release_before_cutoff() -> (
    None
):
    releases = {
        "2026.6.4": [{"upload_time_iso_8601": "2026-06-04T12:00:00Z"}],
        "2026.1.3": [{"upload_time_iso_8601": "2026-01-03T12:00:00Z"}],
        "2025.12.9": [{"upload_time_iso_8601": "2025-12-09T12:00:00Z"}],
        "2025.12.10b0": [{"upload_time_iso_8601": "2025-12-10T12:00:00Z"}],
    }

    assert (
        six_month_old_homeassistant_version(
            now=datetime(2026, 6, 28, tzinfo=timezone.utc),
            releases=releases,
        )
        == "2025.12.9"
    )
