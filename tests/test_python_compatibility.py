"""Ensure the integration remains compatible with supported HA Python versions."""

import ast
from pathlib import Path


def test_custom_component_sources_support_python_313() -> None:
    """Home Assistant 2026.2 runs on Python 3.13."""
    component_path = Path(__file__).parents[1] / "custom_components" / "hubitat"

    for source_path in component_path.rglob("*.py"):
        ast.parse(
            source_path.read_text(),
            filename=str(source_path),
            feature_version=(3, 13),
        )
