from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.services.analytics import GiftPick
from app.services.repository import Repository


@dataclass(slots=True)
class MarketFeed:
    picks: list[GiftPick]
    source_name: str
    updated_at: str


class MarketDataProvider:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    def get_feed(self) -> MarketFeed:
        snapshots = self._repository.list_market_snapshots()
        if not snapshots:
            return MarketFeed(picks=[], source_name="unknown", updated_at=datetime.now(UTC).isoformat())

        picks = [
            GiftPick(
                slug=item.gift_slug,
                title=item.title,
                model=item.model,
                backdrop=item.backdrop,
                image_url=item.image_url,
                image_path=item.image_path,
                price_stars=item.price_stars,
                price_ton=item.price_ton,
                median_stars=item.median_stars,
                median_ton=item.median_ton,
                liquidity=item.liquidity,
                risk=item.risk,
                comment=item.comment,
            )
            for item in snapshots
        ]
        return MarketFeed(
            picks=picks,
            source_name=snapshots[0].source_name,
            updated_at=max(item.updated_at for item in snapshots),
        )
