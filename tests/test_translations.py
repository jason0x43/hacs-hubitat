import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "hubitat"
TRANSLATION_FILES = [
    COMPONENT_DIR / "strings.json",
    *sorted((COMPONENT_DIR / "translations").glob("*.json")),
]


def _strings(value: Any, path: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _strings(child, f"{path}.{key}" if path else key)
    elif isinstance(value, str):
        yield path, value


@pytest.mark.parametrize("file", TRANSLATION_FILES, ids=lambda file: file.name)
def test_translations_have_no_html_like_tags(file: Path) -> None:
    """Home Assistant parses translations as ICU messages, so <...> is a tag.

    A tag that isn't valid HTML shows as "Translation error: INVALID_TAG".
    """
    strings = json.loads(file.read_text())
    bad = [path for path, text in _strings(strings) if "<" in text or ">" in text]
    assert bad == []
