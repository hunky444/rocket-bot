from __future__ import annotations

from dataclasses import dataclass

from app.services.repository import Repository


@dataclass(slots=True)
class PortfolioPosition:
    title: str
    gift_slug: str
    quantity: int
    buy_price_stars: int
    current_price_stars: int
    median_stars: int

    @property
    def pnl_stars(self) -> int:
        return (self.current_price_stars - self.buy_price_stars) * self.quantity


@dataclass(slots=True)
class PortfolioSummary:
    positions: list[PortfolioPosition]
    total_cost_stars: int
    total_floor_value_stars: int

    @property
    def total_pnl_stars(self) -> int:
        return self.total_floor_value_stars - self.total_cost_stars


class PortfolioService:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    def add_demo_item(self, telegram_user_id: int, gift_slug: str) -> PortfolioPosition | None:
        snapshot = self._repository.get_market_snapshot_by_slug(gift_slug)
        if snapshot is None:
            return None
        buy_price = max(snapshot.price_stars - 180, 100)
        self._repository.add_portfolio_item(
            telegram_user_id=telegram_user_id,
            gift_slug=gift_slug,
            buy_price_stars=buy_price,
            quantity=1,
        )
        return PortfolioPosition(
            title=snapshot.title,
            gift_slug=snapshot.gift_slug,
            quantity=1,
            buy_price_stars=buy_price,
            current_price_stars=snapshot.price_stars,
            median_stars=snapshot.median_stars,
        )

    def get_summary(self, telegram_user_id: int) -> PortfolioSummary:
        items = self._repository.list_portfolio_items(telegram_user_id)
        positions: list[PortfolioPosition] = []
        total_cost = 0
        total_floor = 0

        for item in items:
            snapshot = self._repository.get_market_snapshot_by_slug(item.gift_slug)
            if snapshot is None:
                continue
            position = PortfolioPosition(
                title=snapshot.title,
                gift_slug=item.gift_slug,
                quantity=item.quantity,
                buy_price_stars=item.buy_price_stars,
                current_price_stars=snapshot.price_stars,
                median_stars=snapshot.median_stars,
            )
            positions.append(position)
            total_cost += item.buy_price_stars * item.quantity
            total_floor += snapshot.price_stars * item.quantity

        return PortfolioSummary(
            positions=positions,
            total_cost_stars=total_cost,
            total_floor_value_stars=total_floor,
        )
