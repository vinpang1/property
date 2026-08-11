"""Tests for report workspace management."""

import shutil

import pytest

from src.reporting.workspace import (
    archive_report,
    ensure_workspace_dirs,
    in_progress_dir,
    archived_dir,
    list_reports,
)


@pytest.fixture
def workspace_dirs(tmp_path, monkeypatch):
    """Redirect workspace paths to a temp directory."""
    in_prog = tmp_path / "in_progress"
    archived = tmp_path / "archived"
    manufacturing = tmp_path / "manufacturing"
    for d in (in_prog, archived, manufacturing):
        d.mkdir()

    def fake_get_path(key):
        mapping = {
            "workspace_reports_in_progress": in_prog,
            "workspace_reports_archived": archived,
            "workspace_reports_manufacturing": manufacturing,
        }
        return mapping[key]

    monkeypatch.setattr("src.reporting.workspace.get_path", fake_get_path)
    return in_prog, archived


def test_list_reports_empty(workspace_dirs):
    reports = list_reports()
    assert reports["in_progress"] == []
    assert reports["archived"] == []


def test_archive_report(workspace_dirs):
    in_prog, archived = workspace_dirs
    sample = in_prog / "monthly_report_2026-08-05.csv"
    sample.write_text("test data", encoding="utf-8")

    dest = archive_report("monthly_report_2026-08-05.csv")
    assert dest.parent == archived
    assert dest.read_text(encoding="utf-8") == "test data"
    assert not sample.exists()


def test_archive_report_version_conflict(workspace_dirs):
    in_prog, archived = workspace_dirs
    sample = in_prog / "report.csv"
    sample.write_text("v1", encoding="utf-8")
    (archived / "report.csv").write_text("old", encoding="utf-8")

    dest = archive_report("report.csv")
    assert dest.name == "report_v2.csv"
    assert dest.read_text(encoding="utf-8") == "v1"


def test_archive_report_not_found(workspace_dirs):
    with pytest.raises(FileNotFoundError):
        archive_report("nonexistent.csv")
