from pathlib import Path

import yaml

from .paths import PROJECT_ROOT


def load_blueprint(category: str, name: str) -> dict:
    path = PROJECT_ROOT / "blueprints" / category / name
    if not path.exists():
        raise FileNotFoundError(f"Blueprint not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def blueprint_version(category: str, name: str) -> str:
    stem = Path(name).stem
    return f"{category}_{stem}"
