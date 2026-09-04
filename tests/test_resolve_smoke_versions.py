from scripts import resolve_smoke_versions


def test_smoke_matrix_includes_current_historical_and_latest_beta(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        resolve_smoke_versions, "fetch_homeassistant_releases", lambda: {}
    )
    monkeypatch.setattr(
        resolve_smoke_versions,
        "latest_stable_homeassistant_version",
        lambda _: "2026.9.0",
    )
    monkeypatch.setattr(
        resolve_smoke_versions,
        "six_month_old_homeassistant_version",
        lambda *, releases: "2026.2.3",
    )
    monkeypatch.setattr(
        resolve_smoke_versions,
        "next_beta_homeassistant_version",
        lambda *_: "2026.10.0b0",
    )
    assert resolve_smoke_versions.smoke_matrix() == {
        "include": [
            {"label": "current", "ha_version": "2026.9.0"},
            {"label": "6 months ago", "ha_version": "2026.2.3"},
            {"label": "next (latest beta)", "ha_version": "2026.10.0b0"},
        ]
    }


def test_smoke_matrix_skips_beta_when_no_next_beta_is_available(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        resolve_smoke_versions, "fetch_homeassistant_releases", lambda: {}
    )
    monkeypatch.setattr(
        resolve_smoke_versions,
        "latest_stable_homeassistant_version",
        lambda _: "2026.9.0",
    )
    monkeypatch.setattr(
        resolve_smoke_versions,
        "six_month_old_homeassistant_version",
        lambda *, releases: "2026.2.3",
    )
    monkeypatch.setattr(
        resolve_smoke_versions,
        "next_beta_homeassistant_version",
        lambda *_: None,
    )
    assert resolve_smoke_versions.smoke_matrix()["include"] == [
        {"label": "current", "ha_version": "2026.9.0"},
        {"label": "6 months ago", "ha_version": "2026.2.3"},
    ]
