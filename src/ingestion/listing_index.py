"""Index active property listings with agent details for transaction matching."""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterator

from src.ingestion.agent_enrichment import AgentEnricher, AgentInfo, CENTALINE_POST_LIST

MIDLAND_PROPERTIES = "https://data.midland.com.hk/search/v2/properties"
TOKEN_PAGE = "https://www.midland.com.hk/zh-hk/list/transaction"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HKPropertyTracker/0.1)",
    "Platform": "Web",
}


@dataclass
class ListingRecord:
    source: str
    listing_ref: str
    estate_name: str
    block: str
    floor: str
    unit: str
    price: int
    area_sqft: float | None
    agent_name: str = ""
    branch_name: str = ""
    agent_phone: str = ""
    agent_licence: str = ""
    agent_whatsapp: str = ""
    agent_wechat: str = ""
    detail_url: str = ""

    @property
    def normalized_estate(self) -> str:
        return _normalize_text(self.estate_name)

    @property
    def normalized_block(self) -> str:
        return _normalize_text(self.block)

    @property
    def normalized_unit(self) -> str:
        return _normalize_text(self.unit)


def _normalize_text(value: str) -> str:
    cleaned = (value or "").lower()
    cleaned = cleaned.replace(" ", "").replace("　", "")
    cleaned = re.sub(r"[期座樓室層]", "", cleaned)
    return cleaned


def _estate_label(*parts: str | None) -> str:
    return " ".join(part.strip() for part in parts if part and part.strip())


def _fetch_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    request_headers = {**DEFAULT_HEADERS, **(headers or {})}
    data = None
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_midland_token() -> str:
    req = urllib.request.Request(TOKEN_PAGE, headers={"User-Agent": DEFAULT_HEADERS["User-Agent"]})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    match = re.search(r'BUILD_TOKEN":"([^"]+)"', html)
    if not match:
        raise RuntimeError("Unable to locate Midland BUILD_TOKEN")
    return match.group(1)


def iter_centaline_listings(
    *,
    keyword: str = "屯門",
    page_size: int = 100,
    max_pages: int = 5,
    request_interval_seconds: float = 0.2,
) -> Iterator[dict[str, Any]]:
    offset = 0
    pages = 0
    while pages < max_pages:
        body = _fetch_json(
            CENTALINE_POST_LIST,
            method="POST",
            payload={"postType": "Sale", "keyword": keyword, "size": page_size, "offset": offset},
        )
        rows = body.get("data") or []
        if not rows:
            break
        yield from rows
        offset += page_size
        total = int(body.get("count") or 0)
        pages += 1
        if offset >= total:
            break
        time.sleep(request_interval_seconds)


def iter_midland_listings(
    *,
    keyword: str = "屯門",
    page_size: int = 100,
    max_pages: int = 10,
    request_interval_seconds: float = 0.2,
) -> Iterator[dict[str, Any]]:
    token = _fetch_midland_token()
    page = 1
    while page <= max_pages:
        params = {
            "text": keyword,
            "tx_type": "S",
            "page": str(page),
            "limit": str(page_size),
            "lang": "zh-hk",
        }
        url = f"{MIDLAND_PROPERTIES}?{urllib.parse.urlencode(params)}"
        body = _fetch_json(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Origin": "https://www.midland.com.hk",
                "Referer": "https://www.midland.com.hk/",
            },
        )
        rows = body.get("result") or []
        if not rows:
            break
        yield from rows
        if page * page_size >= int(body.get("count") or 0):
            break
        page += 1
        time.sleep(request_interval_seconds)


def _listing_from_centaline(item: dict[str, Any], agent: AgentInfo) -> ListingRecord:
    estate = _estate_label(item.get("bigEstateName"), item.get("estateName"))
    area_info = item.get("areaInfo") or {}
    return ListingRecord(
        source="centaline",
        listing_ref=str(item.get("refNo") or ""),
        estate_name=estate,
        block=str(item.get("buildingName") or ""),
        floor=str(item.get("yAxis") or ""),
        unit=str(item.get("xAxis") or ""),
        price=int((item.get("priceInfo") or {}).get("price") or item.get("propertyPriceHkd") or 0),
        area_sqft=area_info.get("nSize") or area_info.get("size"),
        agent_name=agent.agent_name,
        branch_name=agent.branch_name,
        agent_phone=agent.agent_phone,
        agent_licence=agent.agent_licence,
        agent_whatsapp=agent.agent_whatsapp,
        agent_wechat=agent.agent_wechat,
        detail_url=str(item.get("detailUrl") or ""),
    )


def _listing_from_midland(item: dict[str, Any], agent: AgentInfo) -> ListingRecord:
    estate = _estate_label((item.get("estate") or {}).get("name"), (item.get("phase") or {}).get("name"))
    floor = (item.get("floor_level") or {}).get("name") or ""
    return ListingRecord(
        source="midland",
        listing_ref=str(item.get("serial_no") or ""),
        estate_name=estate,
        block=str((item.get("building") or {}).get("name") or ""),
        floor=str(floor),
        unit=str(item.get("flat") or ""),
        price=int(item.get("price") or 0),
        area_sqft=item.get("net_area") or item.get("area"),
        agent_name=agent.agent_name,
        branch_name=agent.branch_name,
        agent_phone=agent.agent_phone,
        agent_licence=agent.agent_licence,
        agent_whatsapp=agent.agent_whatsapp,
        agent_wechat=agent.agent_wechat,
        detail_url=str(item.get("url_desc") or ""),
    )


def build_listing_index(
    *,
    keyword: str = "屯門",
    request_interval_seconds: float = 0.2,
    max_centaline_pages: int = 5,
    max_midland_pages: int = 10,
) -> list[ListingRecord]:
    listings: list[ListingRecord] = []

    for item in iter_centaline_listings(
        keyword=keyword,
        max_pages=max_centaline_pages,
        request_interval_seconds=request_interval_seconds,
    ):
        listings.append(_listing_from_centaline(item, AgentInfo()))

    enricher = AgentEnricher(request_interval_seconds=request_interval_seconds)
    for item in iter_midland_listings(
        keyword=keyword,
        max_pages=max_midland_pages,
        request_interval_seconds=request_interval_seconds,
    ):
        agent_data = item.get("agent") or {}
        name = agent_data.get("name") or {}
        agent = AgentInfo(
            agent_name=name.get("chi") or name.get("eng") or "",
            branch_name=enricher.resolve_midland_branch(str(agent_data.get("dept_id") or "")),
            agent_phone=str(
                agent_data.get("virtual_phone_no")
                or agent_data.get("agent_mobile_no")
                or agent_data.get("mobile_no")
                or ""
            ),
            agent_licence=str(agent_data.get("licence_no") or ""),
            agent_whatsapp=str(agent_data.get("virtual_phone_no") or ""),
            agent_wechat=str(agent_data.get("wechat_id") or ""),
            listing_ref=str(item.get("serial_no") or ""),
        )
        listings.append(_listing_from_midland(item, agent))

    return listings
