from __future__ import annotations

from dataclasses import dataclass

from app.services.repository import PaymentRecord, Repository, SubscriptionRecord


@dataclass(slots=True)
class PlanOffer:
    code: str
    title: str
    price_stars: int
    features: tuple[str, ...]


class BillingService:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository
        self._offers = {
            "pro": PlanOffer(
                code="pro",
                title="Pro",
                price_stars=399,
                features=(
                    "безлимитные подборки по бюджету",
                    "до 5 результатов в выдаче",
                    "расширенный анализ покупки и продажи",
                ),
            ),
            "premium": PlanOffer(
                code="premium",
                title="Premium",
                price_stars=1190,
                features=(
                    "все из Pro",
                    "быстрые сигналы",
                    "доступ к premium-экранам и будущему портфелю",
                ),
            ),
        }

    def get_offer(self, code: str) -> PlanOffer | None:
        return self._offers.get(code)

    def list_offers(self) -> list[PlanOffer]:
        return list(self._offers.values())

    def create_demo_checkout(self, telegram_user_id: int, plan_code: str) -> PaymentRecord:
        offer = self.get_offer(plan_code)
        if offer is None:
            raise ValueError(f"Unknown plan code: {plan_code}")
        return self._repository.create_payment(
            telegram_user_id=telegram_user_id,
            product_code=offer.code,
            amount_stars=offer.price_stars,
            provider="demo_stars",
            status="pending",
            checkout_url=f"https://example.local/checkout/{offer.code}",
        )

    def confirm_demo_checkout(self, telegram_user_id: int, plan_code: str) -> SubscriptionRecord:
        offer = self.get_offer(plan_code)
        if offer is None:
            raise ValueError(f"Unknown plan code: {plan_code}")
        self._repository.create_payment(
            telegram_user_id=telegram_user_id,
            product_code=offer.code,
            amount_stars=offer.price_stars,
            provider="demo_stars",
            status="paid",
            checkout_url=None,
        )
        return self._repository.activate_subscription(
            telegram_user_id=telegram_user_id,
            plan=offer.code,
            provider="demo_stars",
        )
