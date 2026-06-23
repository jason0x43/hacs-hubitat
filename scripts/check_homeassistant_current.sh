#!/bin/bash

set -euo pipefail

output="$(uv tree --package homeassistant --outdated --frozen --depth 0)"
echo "$output"

if [[ "$output" == *"(latest:"* ]]; then
    echo "Home Assistant is out of date. Run: uv lock --upgrade-package homeassistant"
    exit 1
fi
