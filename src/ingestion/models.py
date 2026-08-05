"""Shared transaction models for multi-source ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.ingestion.transaction_stage import classify_transaction_stage


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
    branch_name: str = ""
    agent_name: str = ""
    agent_phone: str = ""
    agent_licence: str = ""
    agent_whatsapp: str = ""
    agent_wechat: str = ""
    listing_ref: str = ""
    record_source: str = ""
    transaction_stage: str = ""
    detail_url: str = ""

    def to_csv_row(self) -> dict[str, Any]:
        stage = self.transaction_stage or classify_transaction_stage(self.record_source)
        return {
            "屋苑": self.estate_name,
            "座數": self.block,
            "樓層": self.floor,
            "單位": self.unit,
            "實用面積": self.area_sqft or "",
            "成交價": self.price,
            "成交日期": self.transaction_date,
            "成交階段": stage,
            "地區": self.district,
            "分區": self.sub_district,
            "市場類型": self.market_type,
            "地址": self.address,
            "分行": self.branch_name,
            "負責代理": self.agent_name,
            "代理電話": self.agent_phone,
            "代理牌照": self.agent_licence,
            "WhatsApp": self.agent_whatsapp,
            "WeChat": self.agent_wechat,
            "放盤編號": self.listing_ref,
            "成交來源": self.record_source,
            "來源": self.source,
            "來源ID": self.source_id,
            "詳情連結": self.detail_url,
        }
