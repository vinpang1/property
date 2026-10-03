"""Aggregate Tuen Mun property news from major agencies."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import date

from src.ingestion.manyw_client import fetch_tuen_mun_news

NEWS_SOURCES = [
    {
        "source": "centaline",
        "name": "中原地產",
        "url": "https://hk.centanet.com/findproperty/zh-hk/article",
    },
    {
        "source": "midland",
        "name": "美聯物業",
        "url": "https://www.midland.com.hk/zh-hk/news",
    },
    {
        "source": "ricacorp",
        "name": "利嘉閣",
        "url": "https://www.ricacorp.com/zh-hk/articles/",
    },
]


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")


def _extract_articles(html: str, source: str, base_url: str) -> list[dict]:
    articles: list[dict] = []
    seen: set[str] = set()

    for match in re.finditer(
        r"(202[56][-/]\d{2}[-/]\d{2}).{0,120}?([^<]{8,160}屯門[^<]{0,160})",
        html,
        re.S,
    ):
        published = match.group(1).replace("/", "-")
        title = " ".join(re.sub(r"<[^>]+>", " ", match.group(2)).split())
        if not title or "屯門" not in title or len(title) < 12 or len(title) > 120:
            continue
        if title in seen:
            continue
        seen.add(title)
        articles.append(
            {
                "published_date": published[:10],
                "title": title,
                "source": source,
                "url": base_url,
            }
        )

    for match in re.finditer(
        r"<a[^>]+href=\"([^\"]+)\"[^>]*>([^<]*屯門[^<]{0,120})</a>",
        html,
        re.S,
    ):
        href, title = match.group(1), " ".join(match.group(2).split())
        if title in seen:
            continue
        seen.add(title)
        url = href if href.startswith("http") else urllib.parse.urljoin(base_url, href)
        articles.append(
            {
                "published_date": "",
                "title": title,
                "source": source,
                "url": url,
            }
        )

    return articles


def collect_tuen_mun_news_review(limit_per_source: int = 10) -> list[dict]:
    articles: list[dict] = []

    for source in NEWS_SOURCES:
        try:
            html = _fetch(source["url"])
            items = _extract_articles(html, source["source"], source["url"])
            articles.extend(items[:limit_per_source])
        except Exception:
            continue

    articles.extend(fetch_tuen_mun_news(limit=limit_per_source))
    articles.sort(key=lambda item: item.get("published_date") or "", reverse=True)

    deduped: list[dict] = []
    seen: set[str] = set()
    for item in articles:
        key = item["title"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def write_news_review(path: str, articles: list[dict]) -> None:
    from pathlib import Path

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": date.today().isoformat(),
        "district": "屯門區",
        "article_count": len(articles),
        "articles": articles,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
