"""Infer transaction agents by matching listings and news against deal records."""

from __future__ import annotations

from dataclasses import dataclass

from src.ingestion.agent_enrichment import AgentEnricher
from src.ingestion.listing_index import ListingRecord, _normalize_text
from src.ingestion.models import UnitTransaction
from src.ingestion.news_transactions import NewsTransactionClue


@dataclass
class InferenceResult:
    agent_name: str = ""
    branch_name: str = ""
    agent_phone: str = ""
    agent_licence: str = ""
    agent_whatsapp: str = ""
    agent_wechat: str = ""
    listing_ref: str = ""
    inference_source: str = ""
    inference_confidence: str = ""
    inference_evidence: str = ""


def _normalize_estate(value: str) -> str:
    return _normalize_text(value)


def _price_close(left: int, right: int, tolerance: float) -> bool:
    if not left or not right:
        return False
    return abs(left - right) / right <= tolerance


def _estate_matches(tx_estate: str, candidate: str) -> bool:
    left = _normalize_estate(tx_estate)
    right = _normalize_estate(candidate)
    if not left or not right:
        return False
    return left == right or left in right or right in left


def _score_listing_match(tx: UnitTransaction, listing: ListingRecord) -> int:
    if not _estate_matches(tx.estate_name, listing.estate_name):
        return 0

    score = 4
    if tx.unit and listing.unit and _normalize_text(tx.unit) == listing.normalized_unit:
        score += 3
    if tx.block and listing.block:
        if _normalize_text(tx.block) == listing.normalized_block:
            score += 2
        elif _normalize_text(tx.block) in listing.normalized_block or listing.normalized_block in _normalize_text(tx.block):
            score += 1
    if tx.price and listing.price:
        if tx.price == listing.price:
            score += 3
        elif _price_close(tx.price, listing.price, 0.02):
            score += 2
        elif _price_close(tx.price, listing.price, 0.05):
            score += 1
    if tx.area_sqft and listing.area_sqft:
        if abs(tx.area_sqft - listing.area_sqft) <= max(5, listing.area_sqft * 0.05):
            score += 2
    return score


def _confidence_from_score(score: int) -> str:
    if score >= 9:
        return "高"
    if score >= 6:
        return "中"
    if score >= 4:
        return "低"
    return ""


def _result_from_listing(listing: ListingRecord, *, score: int) -> InferenceResult:
    return InferenceResult(
        agent_name=listing.agent_name,
        branch_name=listing.branch_name,
        agent_phone=listing.agent_phone,
        agent_licence=listing.agent_licence,
        agent_whatsapp=listing.agent_whatsapp,
        agent_wechat=listing.agent_wechat,
        listing_ref=listing.listing_ref,
        inference_source=f"放盤配對({listing.source})",
        inference_confidence=_confidence_from_score(score),
        inference_evidence=(
            f"{listing.estate_name} {listing.block} {listing.unit} "
            f"放盤${listing.price:,} 編號{listing.listing_ref}"
        ),
    )


def _score_news_match(tx: UnitTransaction, clue: NewsTransactionClue) -> int:
    if not _estate_matches(tx.estate_name, clue.estate_name):
        return 0

    score = 3
    if clue.price and tx.price:
        if clue.price == tx.price:
            score += 3
        elif _price_close(tx.price, clue.price, 0.05):
            score += 1
    if clue.agent_name:
        score += 2
    return score


def _result_from_news(clue: NewsTransactionClue, *, score: int) -> InferenceResult:
    return InferenceResult(
        agent_name=clue.agent_name,
        inference_source=f"新聞配對({clue.source})",
        inference_confidence=_confidence_from_score(score),
        inference_evidence=clue.evidence,
    )


def infer_agent_for_transaction(
    tx: UnitTransaction,
    *,
    listings: list[ListingRecord],
    news_clues: list[NewsTransactionClue] | None = None,
    enricher: AgentEnricher | None = None,
) -> InferenceResult | None:
    if tx.agent_name:
        return None

    best_listing: tuple[int, ListingRecord] | None = None
    for listing in listings:
        score = _score_listing_match(tx, listing)
        if score < 4:
            continue
        if not best_listing or score > best_listing[0]:
            best_listing = (score, listing)

    best_news: tuple[int, NewsTransactionClue] | None = None
    for clue in news_clues or []:
        score = _score_news_match(tx, clue)
        if score < 4:
            continue
        if not best_news or score > best_news[0]:
            best_news = (score, clue)

    if best_listing and (not best_news or best_listing[0] >= best_news[0]):
        listing = best_listing[1]
        if listing.source == "centaline" and listing.listing_ref and enricher and not listing.agent_name:
            agent = enricher._centaline_post_detail(listing.listing_ref)
            listing = ListingRecord(
                source=listing.source,
                listing_ref=listing.listing_ref,
                estate_name=listing.estate_name,
                block=listing.block,
                floor=listing.floor,
                unit=listing.unit,
                price=listing.price,
                area_sqft=listing.area_sqft,
                agent_name=agent.agent_name,
                branch_name=agent.branch_name,
                agent_phone=agent.agent_phone,
                agent_licence=agent.agent_licence,
                agent_whatsapp=agent.agent_whatsapp,
                agent_wechat=agent.agent_wechat,
                detail_url=listing.detail_url,
            )
        if listing.agent_name or listing.listing_ref:
            return _result_from_listing(listing, score=best_listing[0])
    if best_news:
        return _result_from_news(best_news[1], score=best_news[0])
    return None


def apply_inference(tx: UnitTransaction, result: InferenceResult | None) -> UnitTransaction:
    if not result:
        return tx

    tx.agent_name = tx.agent_name or result.agent_name
    tx.branch_name = tx.branch_name or result.branch_name
    tx.agent_phone = tx.agent_phone or result.agent_phone
    tx.agent_licence = tx.agent_licence or result.agent_licence
    tx.agent_whatsapp = tx.agent_whatsapp or result.agent_whatsapp
    tx.agent_wechat = tx.agent_wechat or result.agent_wechat
    tx.listing_ref = tx.listing_ref or result.listing_ref
    tx.inference_source = result.inference_source
    tx.inference_confidence = result.inference_confidence
    tx.inference_evidence = result.inference_evidence
    return tx


def infer_agents_for_transactions(
    transactions: list[UnitTransaction],
    *,
    listings: list[ListingRecord],
    news_clues: list[NewsTransactionClue] | None = None,
    enricher: AgentEnricher | None = None,
) -> list[UnitTransaction]:
    enricher = enricher or AgentEnricher(request_interval_seconds=0.2)
    enriched: list[UnitTransaction] = []
    for tx in transactions:
        inference = infer_agent_for_transaction(
            tx,
            listings=listings,
            news_clues=news_clues,
            enricher=enricher,
        )
        enriched.append(apply_inference(tx, inference))
    return enriched
