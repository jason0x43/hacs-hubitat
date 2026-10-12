"""Compatibility shims for supporting multiple Home Assistant versions."""

# Home Assistant 2026.10 replaced voluptuous with probatio, an API-compatible
# fork. HA aliases voluptuous to probatio at runtime, but its type hints now
# require probatio types. Older HA versions don't include probatio.
try:
    import probatio as vol
except ImportError:  # HA < 2026.10
    import voluptuous as vol  # type: ignore[no-redef]

__all__ = ["vol"]
