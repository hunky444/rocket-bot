from __future__ import annotations

from dataclasses import dataclass

from app.services.repository import Repository


@dataclass(slots=True)
class UserAlert:
    id: int
    description: str
    status: str


class AlertsService:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    def create_budget_alert(self, telegram_user_id: int, budget_max: int, discount_min_pct: float = 8.0) -> UserAlert:
        record = self._repository.create_alert(
            telegram_user_id=telegram_user_id,
            alert_type="budget_opportunity",
            budget_max=budget_max,
            discount_min_pct=discount_min_pct,
        )
        return UserAlert(
            id=record.id,
            description=f"Сообщать о лотах до {budget_max} Stars с дисконтом от {discount_min_pct:.0f}%",
            status=record.status,
        )

    def list_user_alerts(self, telegram_user_id: int) -> list[UserAlert]:
        records = self._repository.list_alerts(telegram_user_id)
        result: list[UserAlert] = []
        for record in records:
            if record.alert_type == "budget_opportunity":
                description = (
                    f"Лоты до {record.budget_max} Stars"
                    f" с дисконтом от {record.discount_min_pct:.0f}%"
                )
            else:
                description = record.alert_type
            result.append(UserAlert(id=record.id, description=description, status=record.status))
        return result
