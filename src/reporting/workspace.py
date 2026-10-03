"""報告工作區管理 — 進行中、保留、製造目錄。"""

import shutil
from pathlib import Path

from src.utils.config import get_path


def in_progress_dir() -> Path:
    return get_path("workspace_reports_in_progress")


def archived_dir() -> Path:
    return get_path("workspace_reports_archived")


def manufacturing_dir() -> Path:
    return get_path("workspace_reports_manufacturing")


def ensure_workspace_dirs() -> None:
    for d in (in_progress_dir(), archived_dir(), manufacturing_dir()):
        d.mkdir(parents=True, exist_ok=True)


def list_reports() -> dict[str, list[Path]]:
    ensure_workspace_dirs()
    return {
        "in_progress": sorted(in_progress_dir().glob("*.csv")),
        "archived": sorted(archived_dir().glob("*.csv")),
    }


def archive_report(filename: str) -> Path:
    """將進行中嘅報告移至保留目錄。"""
    ensure_workspace_dirs()
    source = in_progress_dir() / filename
    if not source.exists():
        raise FileNotFoundError(f"搵唔到進行中嘅報告: {filename}")

    dest = archived_dir() / filename
    if dest.exists():
        stem, suffix = dest.stem, dest.suffix
        version = 2
        while dest.exists():
            dest = archived_dir() / f"{stem}_v{version}{suffix}"
            version += 1

    shutil.move(str(source), str(dest))
    return dest
