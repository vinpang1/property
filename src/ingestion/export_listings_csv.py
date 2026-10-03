"""Export aggregated Tuen Mun property listings with agent/company counts."""

from __future__ import annotations

import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from src.ingestion.agent_enrichment import AgentEnricher, AgentInfo
from src.ingestion.listing_index import ListingRecord, build_listing_index
from src.utils.config import get_path

SOURCE_LABELS = {
    "centaline": "中原",
    "midland": "美聯",
    "ricacorp": "利嘉閣",
    "manyw": "祥益",
}


@dataclass
class PropertyListingAggregate:
    address: str
    estate_name: str
    block: str
    floor: str
    unit: str
    price: int = 0
    area_sqft: float | None = None
    companies: set[str] = field(default_factory=set)
    agents: list[str] = field(default_factory=list)
    _agent_keys: set[str] = field(default_factory=set)

    def add_listing(self, listing: ListingRecord) -> None:
        company = SOURCE_LABELS.get(listing.source, listing.source)
        self.companies.add(company)
        if listing.price and (not self.price or listing.price < self.price):
            self.price = listing.price
        if listing.area_sqft and not self.area_sqft:
            self.area_sqft = listing.area_sqft

        agent_label = _format_agent_contact(listing, company)
        agent_key = _agent_dedup_key(listing, company)
        if agent_key and agent_key not in self._agent_keys:
            self._agent_keys.add(agent_key)
            self.agents.append(agent_label)

    def to_csv_row(self) -> dict[str, str | int]:
        companies = sorted(self.companies)
        return {
            "樓盤地址": self.address,
            "叫價": self.price or "",
            "實用面積": int(self.area_sqft) if self.area_sqft else "",
            "中介公司": " | ".join(companies),
            "代理及聯絡": " | ".join(self.agents),
            "跟盤代理數": len(self.agents),
            "跟盤公司數": len(self.companies),
        }


def _format_address(listing: ListingRecord) -> str:
    parts = [listing.estate_name, listing.block, listing.floor, listing.unit]
    return " ".join(part.strip() for part in parts if part and part.strip())


def _property_key(listing: ListingRecord) -> tuple[str, str, str, str]:
    return (
        listing.normalized_estate,
        listing.normalized_block,
        listing.normalized_unit,
        listing.normalized_estate + listing.normalized_block + listing.normalized_unit,
    )


def _agent_dedup_key(listing: ListingRecord, company: str) -> str:
    identity = listing.agent_licence or listing.agent_phone or listing.agent_name or listing.listing_ref
    return f"{company}:{identity}"


def _format_agent_contact(listing: ListingRecord, company: str) -> str:
    name = listing.agent_name or "待查"
    phone = listing.agent_phone or listing.agent_whatsapp or ""
    branch = listing.branch_name or ""
    licence = listing.agent_licence or ""

    contact_parts = [part for part in [phone, licence] if part]
    contact = "/".join(contact_parts)
    label = f"{company}-{name}"
    if branch:
        label = f"{label}@{branch}"
    if contact:
        label = f"{label}({contact})"
    return label


def aggregate_listings_by_property(listings: list[ListingRecord]) -> list[PropertyListingAggregate]:
    grouped: dict[tuple[str, str, str], PropertyListingAggregate] = {}

    for listing in listings:
        address = _format_address(listing)
        if not address:
            continue
        key = (
            listing.normalized_estate,
            listing.normalized_block,
            listing.normalized_unit,
        )
        if key not in grouped:
            grouped[key] = PropertyListingAggregate(
                address=address,
                estate_name=listing.estate_name,
                block=listing.block,
                floor=listing.floor,
                unit=listing.unit,
            )
        grouped[key].add_listing(listing)

    return sorted(grouped.values(), key=lambda item: (item.estate_name, item.block, item.unit))


def build_full_listing_index(
    *,
    keyword: str = "屯門",
    request_interval_seconds: float = 0.05,
    max_centaline_pages: int = 10,
    max_midland_pages: int = 15,
    max_workers: int = 8,
) -> list[ListingRecord]:
    """Build listing index with agent details for both Centaline and Midland."""
    from src.ingestion.listing_index import (
        _listing_from_centaline,
        _listing_from_midland,
        iter_centaline_listings,
        iter_midland_listings,
    )

    enricher = AgentEnricher(request_interval_seconds=request_interval_seconds)
    centaline_items = list(
        iter_centaline_listings(
            keyword=keyword,
            max_pages=max_centaline_pages,
            request_interval_seconds=request_interval_seconds,
        )
    )

    def _centaline_with_agent(item: dict) -> ListingRecord:
        ref_no = str(item.get("refNo") or "")
        agent = enricher._centaline_post_detail(ref_no) if ref_no else AgentInfo()
        return _listing_from_centaline(item, agent)

    listings: list[ListingRecord] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_centaline_with_agent, item) for item in centaline_items]
        for future in as_completed(futures):
            listings.append(future.result())

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


def export_tuen_mun_listings_csv(
    *,
    keyword: str = "屯門",
    fetch_agents: bool = True,
) -> tuple[Path, list[PropertyListingAggregate], dict]:
    if fetch_agents:
        listings = build_full_listing_index(keyword=keyword)
    else:
        listings = build_listing_index(keyword=keyword, max_centaline_pages=10, max_midland_pages=15)

    aggregates = aggregate_listings_by_property(listings)
    export_dir = get_path("output") / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y-%m-%d")
    output_path = export_dir / f"屯門樓盤_{today}.csv"

    rows = [item.to_csv_row() for item in aggregates]
    if rows:
        with open(output_path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    multi_company = sum(1 for item in aggregates if item.to_csv_row()["跟盤公司數"] > 1)
    multi_agent = sum(1 for item in aggregates if item.to_csv_row()["跟盤代理數"] > 1)
    stats = {
        "raw_listings": len(listings),
        "properties": len(aggregates),
        "multi_company": multi_company,
        "multi_agent": multi_agent,
    }
    return output_path, aggregates, stats
