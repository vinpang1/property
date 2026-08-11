"""Extract transaction and agent clues from property news headlines."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class NewsTransactionClue:
    title: str
    estate_name: str
    price: int | None
    agent_name: str
    published_date: str
    source: str
    url: str
    evidence: str


PRICE_PATTERNS = [
    re.compile(r"以\s*\$?\s*([\d,.]+)\s*萬"),
    re.compile(r"售\s*\$?\s*([\d,.]+)\s*萬"),
    re.compile(r"成交\s*\$?\s*([\d,.]+)\s*萬"),
    re.compile(r"\$\s*([\d,.]+)\s*萬"),
]

AGENT_PATTERNS = [
    re.compile(r"代理[：:]\s*([^\s，,。]{2,8})"),
    re.compile(r"經紀[：:]\s*([^\s，,。]{2,8})"),
    re.compile(r"由([^，,。]{2,6})促成"),
]


def _parse_price_million(raw: str) -> int:
    return int(float(raw.replace(",", "")) * 10000)


def _extract_estate_name(title: str) -> str:
    patterns = [
        re.compile(r"(屯門[^，,。以售成交]{2,20}?)(?:以|售|成交|單位|高層|中層|低層|\d)"),
        re.compile(r"([^，,。]{2,20}?)(?:以|售)\s*\$?[\d,.]+\s*萬"),
    ]
    for pattern in patterns:
        match = pattern.search(title)
        if match:
            estate = match.group(1).strip(" 的")
            if len(estate) >= 2:
                return estate
    if "屯門" in title:
        return "屯門"
    return ""


def _extract_agent_name(title: str) -> str:
    for pattern in AGENT_PATTERNS:
        match = pattern.search(title)
        if match:
            return match.group(1).strip()
    return ""


def parse_news_article(article: dict) -> NewsTransactionClue | None:
    title = str(article.get("title") or "").strip()
    if not title or "屯門" not in title:
        return None

    price = None
    for pattern in PRICE_PATTERNS:
        match = pattern.search(title)
        if match:
            price = _parse_price_million(match.group(1))
            break

    estate_name = _extract_estate_name(title)
    agent_name = _extract_agent_name(title)
    if not estate_name and not price and not agent_name:
        return None

    return NewsTransactionClue(
        title=title,
        estate_name=estate_name,
        price=price,
        agent_name=agent_name,
        published_date=str(article.get("published_date") or ""),
        source=str(article.get("source") or ""),
        url=str(article.get("url") or ""),
        evidence=title,
    )


def collect_news_transaction_clues(articles: list[dict]) -> list[NewsTransactionClue]:
    clues: list[NewsTransactionClue] = []
    for article in articles:
        clue = parse_news_article(article)
        if clue:
            clues.append(clue)
    return clues
