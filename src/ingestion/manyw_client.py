"""Manyw (祥益) estate transaction and news parser."""

from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from src.ingestion.date_utils import month_cutoff
from src.ingestion.models import UnitTransaction
from src.utils.paths import PROJECT_ROOT

ESTATE_CONFIG = PROJECT_ROOT / "config" / "tuen_mun_estates.yaml"
INFO_URL = "https://www.manyw.com/info/{slug}"
NEWS_URLS = [
    "https://www.manyw.com/",
    "https://www.manyw.com/article/misc/news_article.php",
]


def _load_estates() -> list[dict]:
    with open(ESTATE_CONFIG, encoding="utf-8") as handle:
        return yaml.safe_load(handle)["estates"]


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")


def _parse_price(value: str) -> int:
    cleaned = value.replace(",", "").replace("$", "").strip()
    if "萬" in cleaned:
        return int(float(cleaned.replace("萬", "")) * 10000)
    return int(float(cleaned))


def _parse_info_page(html: str, estate_name: str, slug: str, cutoff: date) -> list[UnitTransaction]:
    transactions: list[UnitTransaction] = []
    for row in re.findall(r"<tr[^>]*>.*?</tr>", html, re.S):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)
        if len(cells) < 5:
            continue
        text_cells = [re.sub(r"<[^>]+>", "", cell).strip() for cell in cells]
        joined = " ".join(text_cells)
        if not re.search(r"202[56]-\d{2}-\d{2}", joined):
            continue

        tx_date_raw = re.search(r"(202[56]-\d{2}-\d{2})", joined)
        price_raw = re.search(r"([\d,]+)\s*萬", joined)
        area_raw = re.search(r"(\d+)\s*呎", joined)
        if not tx_date_raw or not price_raw:
            continue

        tx_date = datetime.strptime(tx_date_raw.group(1), "%Y-%m-%d").date()
        if tx_date < cutoff:
            continue

        block = text_cells[1] if len(text_cells) > 1 else ""
        floor = text_cells[2] if len(text_cells) > 2 else ""
        unit = text_cells[3] if len(text_cells) > 3 else ""
        area = int(area_raw.group(1)) if area_raw else None
        price = _parse_price(price_raw.group(1))
        transactions.append(
            UnitTransaction(
                estate_name=estate_name,
                block=block,
                floor=floor,
                unit=unit,
                area_sqft=area,
                price=price,
                price_per_sqft=round(price / area, 2) if area else None,
                pasp_date=tx_date.isoformat(),
                district="屯門區",
                sub_district="",
                market_type="secondary",
                source="manyw",
                source_id=f"{slug}:{tx_date_raw.group(1)}:{block}:{unit}",
                address=estate_name,
            )
        )
    return transactions


def fetch_tuen_mun_transactions(
    *,
    months_back: int = 6,
    request_interval_seconds: float = 1.0,
) -> list[UnitTransaction]:
    cutoff = month_cutoff(months_back)

    collected: list[UnitTransaction] = []
    for estate in _load_estates():
        slug = estate.get("manyw_slug")
        if not slug:
            continue
        url = INFO_URL.format(slug=urllib.parse.quote(slug))
        try:
            html = _fetch(url)
            collected.extend(_parse_info_page(html, estate["name"], slug, cutoff))
        except Exception:
            continue
        time.sleep(request_interval_seconds)
    return collected


def _is_valid_title(title: str) -> bool:
    lowered = title.lower()
    blocked = ("meta ", "content=", "keywords", "description", "img/", "@type", "schema.org")
    return (
        "屯門" in title
        and len(title) >= 12
        and len(title) <= 120
        and not any(token in lowered for token in blocked)
    )


def _extract_manyw_articles(html: str) -> list[dict]:
    articles: list[dict] = []
    seen: set[str] = set()
    for match in re.finditer(
        r"(\d{4}-\d{2}-\d{2}).{0,40}?([^<]{8,160}屯門[^<]{0,160})",
        html,
        re.S,
    ):
        title = " ".join(re.sub(r"<[^>]+>", " ", match.group(2)).split())
        if not _is_valid_title(title) or title in seen:
            continue
        seen.add(title)
        articles.append(
            {
                "published_date": match.group(1),
                "title": title,
                "source": "manyw",
                "url": "https://www.manyw.com/article/misc/news_article.php",
            }
        )
    for match in re.finditer(r">([^<]{8,160}屯門[^<]{0,160})<", html):
        title = " ".join(match.group(1).split())
        if not _is_valid_title(title) or title in seen:
            continue
        seen.add(title)
        articles.append(
            {
                "published_date": "",
                "title": title,
                "source": "manyw",
                "url": "https://www.manyw.com/article/misc/news_article.php",
            }
        )
    return articles


def fetch_tuen_mun_news(limit: int = 20) -> list[dict]:
    articles: list[dict] = []
    for base_url in NEWS_URLS:
        try:
            html = _fetch(base_url)
            articles.extend(_extract_manyw_articles(html))
        except Exception:
            continue
    articles.sort(key=lambda item: item.get("published_date") or "", reverse=True)
    return articles[:limit]
