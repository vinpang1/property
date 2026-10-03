import csv
from datetime import date, timedelta
from pathlib import Path
from random import choice, randint, uniform

from src.utils.blueprint import load_blueprint
from src.utils.config import get_path
from src.utils.logger import get_logger, log_event
from src.utils.paths import PROJECT_ROOT

logger = get_logger("download_tuen_mun", "ingestion")

SAMPLE_ESTATES = [
    "青山灣",
    "浪琴軒",
    "海翠花園",
    "屯門市廣場",
    "怡樂花園",
    "龍門居",
    "美樂花園",
    "富健花園",
    "兆康苑",
    "山景邨",
]

BLOCKS = ["1座", "2座", "3座", "A座", "B座"]
UNITS = ["A", "B", "C", "D", "E"]


def download_tuen_mun(provider: str = "sample", use_seed: bool = True) -> Path:
    blueprint = load_blueprint("ingestion", "tuen_mun_v1.0.yaml")
    staging_dir = get_path("staging") / "tuen_mun"
    staging_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().strftime("%Y-%m-%d")
    output_path = staging_dir / f"{today}_{provider}_tuen_mun.csv"

    if use_seed:
        seed_path = PROJECT_ROOT / "database" / "seeds" / "tuen_mun_sample.csv"
        if seed_path.exists():
            output_path.write_bytes(seed_path.read_bytes())
            log_event(
                logger,
                "info",
                "Loaded seed data",
                source="seed",
                file=str(output_path),
                rows=_count_rows(output_path),
            )
            return output_path

    rows = _generate_sample_rows(provider, count=20)
    _write_raw_csv(output_path, rows, blueprint)

    log_event(
        logger,
        "info",
        "Download complete",
        source=provider,
        file=str(output_path),
        rows=len(rows),
    )
    return output_path


def _generate_sample_rows(provider: str, count: int) -> list[dict]:
    rows = []
    base_date = date.today()
    for i in range(count):
        area = round(uniform(300, 900), 1)
        price_per_sqft = round(uniform(8000, 14000), 2)
        price = int(area * price_per_sqft)
        tx_date = (base_date - timedelta(days=randint(1, 180))).strftime("%Y-%m-%d")
        rows.append(
            {
                "屋苑": choice(SAMPLE_ESTATES),
                "座數": choice(BLOCKS),
                "樓層": f"{randint(1, 35)}/F",
                "單位": choice(UNITS),
                "實用面積": area,
                "成交價": price,
                "成交日期": tx_date,
                "來源": provider,
            }
        )
    return rows


def _write_raw_csv(path: Path, rows: list[dict], blueprint: dict) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _count_rows(path: Path) -> int:
    with open(path, encoding="utf-8-sig") as f:
        return sum(1 for _ in f) - 1
