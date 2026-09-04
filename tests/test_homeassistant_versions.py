from datetime import datetime, timezone

from scripts.homeassistant_versions import (
    latest_beta_homeassistant_version,
    latest_stable_homeassistant_version,
    next_beta_homeassistant_version,
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


def test_latest_beta_homeassistant_version_ignores_other_prereleases() -> None:
    releases: dict[str, list[dict]] = {
        "2026.6.4": [],
        "2026.7.0b2": [],
        "2026.7.0b10": [],
        "2026.7.0rc1": [],
        "2026.8.0.dev0": [],
    }

    assert latest_beta_homeassistant_version(releases) == "2026.7.0b10"


def test_next_beta_homeassistant_version_ignores_betas_for_current_release() -> None:
    releases: dict[str, list[dict]] = {
        "2026.9.0": [],
        "2026.9.0b9": [],
        "2026.10.0b0": [],
    }

    assert next_beta_homeassistant_version("2026.9.0", releases) == "2026.10.0b0"


def test_next_beta_homeassistant_version_returns_none_without_next_beta() -> None:
    releases: dict[str, list[dict]] = {
        "2026.9.0": [],
        "2026.9.0b9": [],
    }

    assert next_beta_homeassistant_version("2026.9.0", releases) is None


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
