from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class GiftPick:
    slug: str
    title: str
    model: str
    backdrop: str
    image_url: str
    image_path: str
    price_stars: int
    price_ton: float
    median_stars: int
    median_ton: float
    liquidity: str
    risk: str
    comment: str

    @property
    def discount_pct(self) -> float:
        if self.median_stars <= 0:
            return 0.0
        return round((self.median_stars - self.price_stars) / self.median_stars * 100, 1)


@dataclass(slots=True)
class SellRecommendation:
    title: str
    quick_sell_stars: int
    market_sell_stars: int
    aggressive_sell_stars: int
    suggestion: str


class MarketFeedProvider(Protocol):
    def get_feed(self) -> object:
        ...


class AnalyticsService:
    def __init__(self, market_provider: MarketFeedProvider) -> None:
        self._market_provider = market_provider

    def extract_budget(self, raw_text: str) -> int | None:
        match = re.search(r"(\d{2,})", raw_text)
        if not match:
            return None
        return int(match.group(1))

    def extract_budget_request(self, raw_text: str) -> tuple[int, str] | None:
        amount = self.extract_budget(raw_text)
        if amount is None:
            return None
        normalized = raw_text.lower()
        if any(token in normalized for token in (" ton", " тон", "тона", "тонов", "tons")):
            return amount, "TON"
        return amount, "XTR"

    def get_best_buys(self, budget: int, plan: str, currency: str = "XTR") -> list[GiftPick]:
        if currency == "TON":
            candidates = [
                pick for pick in self._market_provider.get_feed().picks
                if pick.price_ton > 0 and pick.price_ton <= budget
            ]
            strong_fit = [pick for pick in candidates if pick.price_ton >= budget * 0.5]
            if strong_fit:
                candidates = strong_fit
            candidates.sort(key=lambda item: (item.discount_pct, item.price_ton), reverse=True)
        else:
            candidates = [pick for pick in self._market_provider.get_feed().picks if pick.price_stars <= budget]
            strong_fit = [pick for pick in candidates if pick.price_stars >= int(budget * 0.5)]
            if strong_fit:
                candidates = strong_fit
            candidates.sort(key=lambda item: (item.discount_pct, item.price_stars), reverse=True)

        if plan == "free":
            return candidates[:2]
        if plan == "pro":
            return candidates[:5]
        return candidates[:10]

    def get_top_picks(self, limit: int = 5) -> list[GiftPick]:
        return sorted(self._market_provider.get_feed().picks, key=lambda item: item.discount_pct, reverse=True)[:limit]

    def get_sell_recommendation(self) -> SellRecommendation:
        top_pick = self._market_provider.get_feed().picks[0]
        return SellRecommendation(
            title=top_pick.title,
            quick_sell_stars=top_pick.price_stars + 170,
            market_sell_stars=top_pick.median_stars - 50,
            aggressive_sell_stars=top_pick.median_stars + 230,
            suggestion=(
                "Если нужен быстрый выход, ставь ближе к 2950 Stars. "
                "Если не спешишь, рыночный диапазон выглядит как 3140-3420 Stars."
            ),
        )

    def get_market_summary(self) -> tuple[str, str]:
        feed = self._market_provider.get_feed()
        return feed.source_name, feed.updated_at

    def detect_intent(self, text: str) -> str:
        normalized = text.lower()
        if any(word in normalized for word in ("продать", "продав", "sell", "сливать", "выход")):
            return "sell"
        if any(word in normalized for word in ("портфель", "portfolio")):
            return "portfolio"
        if any(word in normalized for word in ("алерт", "alert", "уведом", "отслеж")):
            return "alerts"
        if any(word in normalized for word in ("топ", "лучшие", "выгод", "top", "недооцен", "перспектив")):
            return "top"
        if any(word in normalized for word in ("купить", "покуп", "buy", "взять", "бюджет", "на ", "до ")) or "stars" in normalized:
            return "buy"
        if self.extract_budget(text) is not None:
            return "buy"
        return "unknown"
