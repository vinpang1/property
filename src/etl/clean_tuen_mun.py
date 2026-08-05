import csv
from datetime import datetime
from pathlib import Path

from src.etl.normalize import normalize_row
from src.utils.blueprint import load_blueprint
from src.utils.config import get_path
from src.utils.logger import get_logger, log_event

logger = get_logger("clean_tuen_mun", "etl")

STANDARD_FIELDS = [
    "estate_name",
    "block",
    "floor",
    "unit",
    "area_sqft",
    "price",
    "price_per_sqft",
    "transaction_date",
    "market_type",
    "source",
]


def clean_tuen_mun(input_path: Path | None = None) -> Path:
    ingestion_bp = load_blueprint("ingestion", "tuen_mun_v1.0.yaml")
    etl_bp = load_blueprint("etl", "tuen_mun_v1.0.yaml")

    if input_path is None:
        staging_dir = get_path("staging") / "tuen_mun"
        candidates = sorted(staging_dir.glob("*.csv"), reverse=True)
        if not candidates:
            raise FileNotFoundError("No staging CSV found for Tuen Mun")
        input_path = candidates[0]

    mapping = ingestion_bp["column_mapping"]
    rules = etl_bp["rules"]
    default_market_type = rules.get("market_type", {}).get("default", "secondary")

    raw_rows = _read_raw_csv(input_path)
    cleaned_rows = []
    seen_keys: set[tuple] = set()
    dedup_key = rules["dedup"]["key"]

    for raw in raw_rows:
        mapped = _map_columns(raw, mapping)
        mapped = normalize_row(mapped, rules.get("address_normalize", []))

        if not mapped.get("price") or not mapped.get("transaction_date"):
            continue

        price = int(float(str(mapped["price"]).replace(",", "")))
        area = float(mapped["area_sqft"]) if mapped.get("area_sqft") else None
        price_per_sqft = round(price / area, 2) if area else None

        row = {
            "estate_name": mapped["estate_name"],
            "block": mapped.get("block"),
            "floor": mapped.get("floor"),
            "unit": mapped.get("unit"),
            "area_sqft": area,
            "price": price,
            "price_per_sqft": price_per_sqft,
            "transaction_date": _normalize_date(mapped["transaction_date"]),
            "market_type": mapped.get("market_type") or default_market_type,
            "source": mapped.get("source") or "unknown",
        }

        key = tuple(row.get(k) for k in dedup_key)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        cleaned_rows.append(row)

    processed_dir = get_path("processed")
    processed_dir.mkdir(parents=True, exist_ok=True)
    output_path = processed_dir / f"cleaned_{input_path.name}"

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=STANDARD_FIELDS)
        writer.writeheader()
        writer.writerows(cleaned_rows)

    log_event(
        logger,
        "info",
        "ETL complete",
        input=str(input_path),
        output=str(output_path),
        rows_in=len(raw_rows),
        rows_out=len(cleaned_rows),
    )
    return output_path


def _read_raw_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _map_columns(raw: dict, mapping: dict) -> dict:
    result = {}
    for standard_field, aliases in mapping.items():
        for alias in aliases:
            if alias in raw and raw[alias]:
                result[standard_field] = raw[alias]
                break
    if "來源" in raw and raw["來源"]:
        result["source"] = raw["來源"]
    return result


def _normalize_date(value: str) -> str:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value.strip()
