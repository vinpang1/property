"""Download HKMC high-LTV mortgage guidelines and premium rate sheets."""

import csv
import hashlib
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.utils.blueprint import load_blueprint
from src.utils.config import get_path
from src.utils.logger import get_logger, log_event

logger = get_logger("download_mortgage", "ingestion")


def download_mortgage() -> Path:
    """Download HKMC mortgage insurance guidelines and premium PDFs."""
    blueprint = load_blueprint("ingestion", "mortgage_v1.0.yaml")
    download_cfg = blueprint.get("download", {})
    resources = blueprint.get("resources", [])

    downloads_dir = get_path("downloads") / "hkmc"
    downloads_dir.mkdir(parents=True, exist_ok=True)

    staging_dir = get_path("staging") / "mortgage"
    staging_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().strftime("%Y-%m-%d")
    manifest_path = staging_dir / f"{today}_mortgage_manifest.csv"

    manifest_rows: list[dict] = []
    downloaded = 0
    skipped = 0
    failed = 0

    for resource in resources:
        result = _download_resource(resource, downloads_dir, download_cfg)
        manifest_rows.append(result)

        if result["status"] == "downloaded":
            downloaded += 1
        elif result["status"] == "skipped":
            skipped += 1
        else:
            failed += 1

        interval = download_cfg.get("request_interval_seconds", 2)
        if interval:
            time.sleep(interval)

    _write_manifest(manifest_path, manifest_rows)

    log_event(
        logger,
        "info",
        "Mortgage data download complete",
        file=str(manifest_path),
        downloaded=downloaded,
        skipped=skipped,
        failed=failed,
        total=len(resources),
    )
    return manifest_path


def _download_resource(
    resource: dict,
    downloads_dir: Path,
    download_cfg: dict,
) -> dict:
    resource_id = resource["id"]
    url = resource["url"]
    filename = resource["filename"]
    output_path = downloads_dir / filename

    base_row = {
        "resource_id": resource_id,
        "category": resource.get("category", ""),
        "name": resource.get("name", ""),
        "description": resource.get("description", ""),
        "url": url,
        "local_path": str(output_path),
        "downloaded_at": "",
        "file_size_bytes": 0,
        "sha256": "",
        "status": "failed",
        "error": "",
    }

    if output_path.exists() and output_path.stat().st_size > 0:
        base_row.update(
            {
                "downloaded_at": datetime.fromtimestamp(
                    output_path.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
                "file_size_bytes": output_path.stat().st_size,
                "sha256": _file_sha256(output_path),
                "status": "skipped",
            }
        )
        log_event(
            logger,
            "info",
            "File already exists, skipping download",
            resource_id=resource_id,
            file=str(output_path),
        )
        return base_row

    retry = download_cfg.get("retry", 3)
    retry_delay = download_cfg.get("retry_delay_seconds", 5)
    user_agent = download_cfg.get(
        "user_agent", "HK-Property-Tracker/0.1 (mortgage-data-ingestion)"
    )

    last_error = ""
    for attempt in range(1, retry + 1):
        try:
            request = Request(url, headers={"User-Agent": user_agent})
            with urlopen(request, timeout=60) as response:
                content = response.read()

            if not content:
                raise ValueError("Empty response body")

            output_path.write_bytes(content)
            base_row.update(
                {
                    "downloaded_at": datetime.now(timezone.utc).isoformat(),
                    "file_size_bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "status": "downloaded",
                }
            )
            log_event(
                logger,
                "info",
                "Downloaded mortgage resource",
                resource_id=resource_id,
                file=str(output_path),
                bytes=len(content),
                attempt=attempt,
            )
            return base_row

        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            last_error = str(exc)
            log_event(
                logger,
                "warning",
                "Download attempt failed",
                resource_id=resource_id,
                attempt=attempt,
                error=last_error,
            )
            if attempt < retry:
                time.sleep(retry_delay)

    base_row["error"] = last_error
    log_event(
        logger,
        "error",
        "Failed to download mortgage resource",
        resource_id=resource_id,
        url=url,
        error=last_error,
    )
    return base_row


def _write_manifest(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "resource_id",
        "category",
        "name",
        "description",
        "url",
        "local_path",
        "downloaded_at",
        "file_size_bytes",
        "sha256",
        "status",
        "error",
    ]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
