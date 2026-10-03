from functools import lru_cache
from pathlib import Path

import yaml

from .paths import PROJECT_ROOT

CONFIG_DIR = PROJECT_ROOT / "config"


@lru_cache
def get_settings() -> dict:
    with open(CONFIG_DIR / "settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def get_sources() -> dict:
    with open(CONFIG_DIR / "sources.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def get_districts() -> dict:
    with open(CONFIG_DIR / "districts.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_path(key: str) -> Path:
    settings = get_settings()
    return PROJECT_ROOT / settings["paths"][key]


def get_db_path(db_name: str) -> Path:
    settings = get_settings()
    return PROJECT_ROOT / settings["database"][db_name]
