from __future__ import annotations

from app.services.repository import Repository, UserRecord


class SubscriptionService:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository
        self._daily_free_budget_limit = 5

    def ensure_user(self, telegram_user_id: int, username: str | None = None, first_name: str | None = None) -> UserRecord:
        self._repository.reset_usage_if_needed(telegram_user_id)
        return self._repository.get_or_create_user(telegram_user_id, username, first_name)

    def can_use_budget_query(self, user: UserRecord) -> bool:
        if user.plan != "free":
            return True
        return user.daily_budget_queries < self._daily_free_budget_limit

    def register_budget_query(self, user: UserRecord) -> UserRecord:
        if user.plan != "free":
            return user
        return self._repository.bump_budget_query(user.telegram_user_id)

    def get_budget_queries_left(self, user: UserRecord) -> int | None:
        if user.plan != "free":
            return None
        return max(self._daily_free_budget_limit - user.daily_budget_queries, 0)

    def set_plan(self, telegram_user_id: int, plan: str) -> UserRecord:
        return self._repository.set_plan(telegram_user_id, plan)
