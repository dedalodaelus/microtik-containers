#!/usr/bin/env python3
"""List buildable container components as a JSON array."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
containers = []
for path in sorted((root / "containers").iterdir()):
    if path.is_dir() and (path / "metadata.env").is_file() and (path / "build.sh").is_file():
        containers.append(path.name)
print(json.dumps(containers, separators=(",", ":")))
