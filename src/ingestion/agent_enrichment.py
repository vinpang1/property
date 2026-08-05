"""Resolve branch and agent details from agency listing pages."""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

CENTALINE_POST_DETAIL = "https://hk.centanet.com/findproperty/api/Post/Detail"
CENTALINE_POST_LIST = "https://hk.centanet.com/findproperty/api/Post/Search"
MIDLAND_PROPERTIES = "https://data.midland.com.hk/search/v2/properties"
MIDLAND_BRANCH = "https://www.midland.com.hk/zh-hk/branch/x-{dept_id}"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HKPropertyTracker/0.1)",
    "Platform": "Web",
}


@dataclass
class AgentInfo:
    agent_name: str = ""
    branch_name: str = ""


class AgentEnricher:
    def __init__(self, *, request_interval_seconds: float = 0.25) -> None:
        self.request_interval_seconds = request_interval_seconds
        self._branch_cache: dict[str, str] = {}
        self._post_detail_cache: dict[str, AgentInfo] = {}
        self._post_search_cache: dict[str, list[dict[str, Any]]] = {}

    def _sleep(self) -> None:
        if self.request_interval_seconds > 0:
            time.sleep(self.request_interval_seconds)

    def _fetch_json(
        self,
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

    def _fetch_html(self, url: str) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_HEADERS["User-Agent"]})
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.read().decode("utf-8", "ignore")

    def resolve_midland_branch(self, dept_id: str) -> str:
        if not dept_id:
            return ""
        if dept_id in self._branch_cache:
            return self._branch_cache[dept_id]

        branch_name = ""
        try:
            html = self._fetch_html(MIDLAND_BRANCH.format(dept_id=dept_id))
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
            if match:
                page_props = json.loads(match.group(1))["props"]["pageProps"]
                branch_data = (page_props.get("result") or {}).get("branchData") or {}
                branch_name = branch_data.get("alt_name") or branch_data.get("name") or page_props.get("branchName") or ""
        except Exception:
            branch_name = ""

        self._branch_cache[dept_id] = branch_name
        self._sleep()
        return branch_name

    def resolve_midland_agent(
        self,
        *,
        token: str,
        estate_id: str,
        flat: str,
        price: int,
        record_source: str,
    ) -> AgentInfo:
        if record_source == "LANDREG" or not estate_id:
            return AgentInfo()

        params = {
            "estate_id": estate_id,
            "tx_type": "S",
            "page": "1",
            "limit": "20",
            "lang": "zh-hk",
        }
        if flat:
            params["flat"] = flat
        if price:
            params["price_from"] = str(max(price - 10000, 0))
            params["price_to"] = str(price + 10000)

        url = f"{MIDLAND_PROPERTIES}?{urllib.parse.urlencode(params)}"
        try:
            body = self._fetch_json(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Origin": "https://www.midland.com.hk",
                    "Referer": "https://www.midland.com.hk/",
                },
            )
        except Exception:
            return AgentInfo()
        finally:
            self._sleep()

        best_agent: dict[str, Any] | None = None
        for item in body.get("result") or []:
            item_price = int(item.get("price") or 0)
            item_flat = str(item.get("flat") or "")
            if price and item_price != price:
                continue
            if flat and item_flat and item_flat != flat:
                continue
            best_agent = item.get("agent") or {}
            break

        if not best_agent and body.get("result"):
            best_agent = (body["result"][0] or {}).get("agent") or {}

        if not best_agent:
            return AgentInfo()

        name = best_agent.get("name") or {}
        agent_name = name.get("chi") or name.get("eng") or ""
        branch_name = self.resolve_midland_branch(str(best_agent.get("dept_id") or ""))
        return AgentInfo(agent_name=agent_name, branch_name=branch_name)

    def _centaline_post_detail(self, ref_no: str) -> AgentInfo:
        if ref_no in self._post_detail_cache:
            return self._post_detail_cache[ref_no]

        info = AgentInfo()
        try:
            detail = self._fetch_json(f"{CENTALINE_POST_DETAIL}?refNo={urllib.parse.quote(ref_no)}")
            agents = detail.get("postAgents") or []
            if agents:
                primary = agents[0]
                info = AgentInfo(
                    agent_name=primary.get("agentNameC") or primary.get("agentNameE") or "",
                    branch_name=primary.get("branchName") or "",
                )
        except Exception:
            info = AgentInfo()

        self._post_detail_cache[ref_no] = info
        self._sleep()
        return info

    def _centaline_search_posts(self, keyword: str) -> list[dict[str, Any]]:
        cache_key = keyword.strip().lower()
        if cache_key in self._post_search_cache:
            return self._post_search_cache[cache_key]

        posts: list[dict[str, Any]] = []
        try:
            body = self._fetch_json(
                CENTALINE_POST_LIST,
                method="POST",
                payload={"postType": "Sale", "keyword": keyword, "size": 50, "offset": 0},
            )
            posts = body.get("data") or []
        except Exception:
            posts = []

        self._post_search_cache[cache_key] = posts
        self._sleep()
        return posts

    def resolve_centaline_agent(self, item: dict[str, Any]) -> AgentInfo:
        record_source = str(item.get("dataSource") or "")
        if record_source != "AC":
            return AgentInfo()

        price = int(item.get("transactionPrice") or 0)
        building = str(item.get("buildingName") or "")
        area = item.get("nArea")
        keywords = [
            " ".join(
                part
                for part in [
                    item.get("bigEstateName"),
                    item.get("estateName"),
                    item.get("buildingName"),
                ]
                if part
            ).strip(),
            str(item.get("bigEstateName") or item.get("estateName") or "").strip(),
        ]

        ref_no = ""
        for keyword in keywords:
            if not keyword:
                continue
            for post in self._centaline_search_posts(keyword):
                post_price = int((post.get("priceInfo") or {}).get("price") or post.get("propertyPriceHkd") or 0)
                post_building = str(post.get("buildingName") or "")
                post_area = (post.get("areaInfo") or {}).get("nSize")
                if price and post_price and post_price != price:
                    continue
                if building and post_building and building != post_building:
                    continue
                if area and post_area and int(post_area) != int(area):
                    continue
                ref_no = str(post.get("refNo") or "")
                if ref_no:
                    break
            if ref_no:
                break

        if not ref_no:
            return AgentInfo()

        return self._centaline_post_detail(ref_no)
