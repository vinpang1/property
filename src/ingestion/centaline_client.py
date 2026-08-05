"""Centaline / Centanet transaction search client."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterator

SEARCH_URL = "https://hk.centanet.com/findproperty/api/Transaction/Search"
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Platform": "Web",
    "User-Agent": "Mozilla/5.0 (compatible; HKPropertyTracker/0.1)",
}


@dataclass
class UnitTransaction:
    estate_name: str
    block: str
    floor: str
    unit: str
    area_sqft: float | None
    price: int
    price_per_sqft: float | None
    transaction_date: str
    district: str
    sub_district: str
    market_type: str
    source: str
    source_id: str
    address: str

    def to_csv_row(self) -> dict[str, Any]:
        return {
            "屋苑": self.estate_name,
            "座數": self.block,
            "樓層": self.floor,
            "單位": self.unit,
            "實用面積": self.area_sqft or "",
            "成交價": self.price,
            "成交日期": self.transaction_date,
            "地區": self.district,
            "分區": self.sub_district,
            "市場類型": self.market_type,
            "地址": self.address,
            "來源": self.source,
            "來源ID": self.source_id,
        }


def _request_interval(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def _post_search(payload: dict[str, Any], retry: int = 3, delay: float = 2.0) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    last_error: Exception | None = None

    for attempt in range(retry):
        try:
            req = urllib.request.Request(SEARCH_URL, data=data, headers=DEFAULT_HEADERS, method="POST")
            with urllib.request.urlopen(req, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
            if body.get("title"):
                raise RuntimeError(body.get("title"))
            return body
        except Exception as exc:
            last_error = exc
            if attempt < retry - 1:
                time.sleep(delay)
    raise RuntimeError(f"Centaline search failed: {last_error}") from last_error


def _parse_date(item: dict[str, Any]) -> str:
    raw = item.get("insDate") or item.get("regDate") or ""
    if not raw:
        return ""
    return raw[:10]


def _parse_market_type(item: dict[str, Any]) -> str:
    hand = (item.get("firstOrSecondHand") or "").lower()
    if hand == "firsthand":
        return "primary"
    if hand == "secondhand":
        return "secondary"
    return hand or "unknown"


def _to_transaction(item: dict[str, Any]) -> UnitTransaction:
    scope = item.get("scope") or {}
    estate = item.get("estateName") or item.get("bigEstateName") or ""
    if item.get("bigEstateName") and item.get("estateName"):
        estate = f"{item['bigEstateName']} {item['estateName']}".strip()

    addr = (item.get("displayText") or {}).get("addr") or {}
    line1 = addr.get("line1") or ""

    return UnitTransaction(
        estate_name=estate or line1,
        block=item.get("buildingName") or "",
        floor=item.get("yAxis") or "",
        unit=item.get("xAxis") or "",
        area_sqft=item.get("nArea") or item.get("gArea"),
        price=int(item.get("transactionPrice") or 0),
        price_per_sqft=item.get("nUnitPrice") or item.get("gUnitPrice"),
        transaction_date=_parse_date(item),
        district=scope.get("db") or item.get("districtName") or "",
        sub_district=scope.get("hma") or item.get("districtName") or "",
        market_type=_parse_market_type(item),
        source="centaline",
        source_id=item.get("id") or "",
        address=item.get("address") or line1,
    )


def iter_transactions(
    *,
    keyword: str | None = None,
    day: str = "Day1095",
    page_size: int = 100,
    request_interval_seconds: float = 0.5,
) -> Iterator[UnitTransaction]:
    offset = 0
    while True:
        payload = {
            "postType": "Sale",
            "day": day,
            "sort": "InsOrRegDate",
            "order": "Descending",
            "size": page_size,
            "offset": offset,
        }
        if keyword:
            payload["keyword"] = keyword

        result = _post_search(payload)
        rows = result.get("data") or []
        if not rows:
            break

        for item in rows:
            yield _to_transaction(item)

        offset += page_size
        total = int(result.get("count") or 0)
        if offset >= total:
            break
        _request_interval(request_interval_seconds)


def fetch_transactions_for_months(
    *,
    year: int,
    months: list[int],
    keyword: str = "屯門",
    day: str = "Day1095",
    request_interval_seconds: float = 0.5,
) -> list[UnitTransaction]:
    wanted = {(year, month) for month in months}
    collected: list[UnitTransaction] = []

    for tx in iter_transactions(
        keyword=keyword,
        day=day,
        request_interval_seconds=request_interval_seconds,
    ):
        if not tx.transaction_date:
            continue
        dt = datetime.strptime(tx.transaction_date, "%Y-%m-%d")
        if (dt.year, dt.month) in wanted:
            collected.append(tx)

    return collected
