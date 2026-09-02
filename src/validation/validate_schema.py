import csv
from datetime import date, datetime
from pathlib import Path

from src.utils.blueprint import load_blueprint
from src.utils.config import get_path
from src.utils.logger import get_logger, log_event

logger = get_logger("validate_schema", "etl")

REQUIRED_FIELDS = ["estate_name", "price", "transaction_date"]


def validate_tuen_mun(csv_path: Path | None = None) -> dict:
    etl_bp = load_blueprint("etl", "tuen_mun_v1.0.yaml")
    rules = etl_bp["rules"]

    if csv_path is None:
        processed_dir = get_path("processed")
        candidates = sorted(processed_dir.glob("cleaned_*.csv"), reverse=True)
        if not candidates:
            raise FileNotFoundError("No processed CSV found for validation")
        csv_path = candidates[0]

    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    errors = []
    valid_rows = 0

    for i, row in enumerate(rows, start=2):
        row_errors = _validate_row(row, rules)
        if row_errors:
            errors.extend([f"Row {i}: {e}" for e in row_errors])
        else:
            valid_rows += 1

    result = {
        "file": csv_path.name,
        "total_rows": len(rows),
        "valid_rows": valid_rows,
        "error_count": len(errors),
        "passed": len(errors) == 0,
        "errors": errors[:20],
    }

    level = "info" if result["passed"] else "warning"
    log_event(logger, level, "Validation complete", **{k: v for k, v in result.items() if k != "errors"})

    if not result["passed"]:
        raise ValueError(f"Validation failed with {len(errors)} errors")

    return result


def _validate_row(row: dict, rules: dict) -> list[str]:
    errors = []

    for field in REQUIRED_FIELDS:
        if not row.get(field):
            errors.append(f"missing required field '{field}'")

    if row.get("price"):
        price = float(row["price"])
        price_rules = rules.get("price", {})
        if price < price_rules.get("min", 0):
            errors.append(f"price {price} below minimum")
        if price > price_rules.get("max", float("inf")):
            errors.append(f"price {price} above maximum")

    if row.get("area_sqft"):
        area = float(row["area_sqft"])
        area_rules = rules.get("area", {})
        if area < area_rules.get("min", 0):
            errors.append(f"area {area} below minimum")
        if area > area_rules.get("max", float("inf")):
            errors.append(f"area {area} above maximum")

    if row.get("transaction_date"):
        try:
            tx_date = datetime.strptime(row["transaction_date"], "%Y-%m-%d").date()
            if tx_date > date.today():
                errors.append(f"transaction_date {tx_date} is in the future")
        except ValueError:
            errors.append(f"invalid transaction_date format: {row['transaction_date']}")

    return errors
