from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, replace

from app.services.repository import LeaderboardEntry, Repository, RocketHistoryRecord, RocketStatsRecord


@dataclass(slots=True)
class RocketRound:
    telegram_user_id: int
    currency: str
    bet_amount: float
    crash_multiplier: float
    current_multiplier: float
    auto_cashout_multiplier: float | None
    status: str
    payout_amount: float
    created_monotonic: float


class RocketService:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository
        self._active_rounds: dict[int, RocketRound] = {}
        self._lock = asyncio.Lock()
        self._min_bet_stars = 100
        self._min_bet_ton = 0.5
        self._default_balance_stars = 10_000
        self._default_balance_ton = 25.0

    @property
    def min_bet_stars(self) -> int:
        return self._min_bet_stars

    @property
    def min_bet_ton(self) -> float:
        return self._min_bet_ton

    @property
    def default_balance_stars(self) -> int:
        return self._default_balance_stars

    @property
    def default_balance_ton(self) -> float:
        return self._default_balance_ton

    async def start_round(
        self,
        telegram_user_id: int,
        currency: str,
        bet_amount: float,
        auto_cashout_multiplier: float | None = None,
    ) -> RocketRound:
        normalized_currency = currency.upper()
        safe_bet = self._normalize_amount(normalized_currency, bet_amount)
        safe_auto = round(auto_cashout_multiplier, 2) if auto_cashout_multiplier is not None else None
        async with self._lock:
            if telegram_user_id in self._active_rounds:
                raise ValueError("active_round")

            user = self._repository.get_user(telegram_user_id)
            if user is None:
                raise ValueError("user_not_found")

            if safe_auto is not None and safe_auto <= 1.0:
                raise ValueError("invalid_auto_cashout")

            if normalized_currency == "XTR":
                if safe_bet < self._min_bet_stars:
                    raise ValueError("bet_too_small")
                if safe_bet > user.demo_balance_stars:
                    raise ValueError("insufficient_balance")
                self._repository.change_demo_balance(telegram_user_id, -int(safe_bet))
            elif normalized_currency == "TON":
                if safe_bet < self._min_bet_ton:
                    raise ValueError("bet_too_small")
                if safe_bet > user.demo_balance_ton:
                    raise ValueError("insufficient_balance")
                self._repository.change_demo_ton_balance(telegram_user_id, -safe_bet)
            else:
                raise ValueError("unsupported_currency")

            round_state = RocketRound(
                telegram_user_id=telegram_user_id,
                currency=normalized_currency,
                bet_amount=safe_bet,
                crash_multiplier=self._generate_crash_multiplier(),
                current_multiplier=1.00,
                auto_cashout_multiplier=safe_auto,
                status="flying",
                payout_amount=0,
                created_monotonic=time.monotonic(),
            )
            self._active_rounds[telegram_user_id] = round_state
            return replace(round_state)

    async def tick_round(self, telegram_user_id: int) -> RocketRound | None:
        async with self._lock:
            round_state = self._active_rounds.get(telegram_user_id)
            if round_state is None:
                return None

            multiplier = self._calculate_multiplier(round_state.created_monotonic)
            if multiplier >= round_state.crash_multiplier:
                round_state.current_multiplier = round_state.crash_multiplier
                round_state.status = "crashed"
                self._active_rounds.pop(telegram_user_id, None)
                self._record_round(round_state)
                return replace(round_state)

            round_state.current_multiplier = multiplier
            if round_state.auto_cashout_multiplier is not None and multiplier >= round_state.auto_cashout_multiplier:
                self._apply_cashout(round_state)
                self._active_rounds.pop(telegram_user_id, None)
            return replace(round_state)

    async def cash_out(self, telegram_user_id: int) -> RocketRound | None:
        async with self._lock:
            round_state = self._active_rounds.get(telegram_user_id)
            if round_state is None:
                return None

            multiplier = self._calculate_multiplier(round_state.created_monotonic)
            if multiplier >= round_state.crash_multiplier:
                round_state.current_multiplier = round_state.crash_multiplier
                round_state.status = "crashed"
                self._active_rounds.pop(telegram_user_id, None)
                self._record_round(round_state)
                return replace(round_state)

            round_state.current_multiplier = multiplier
            self._apply_cashout(round_state)
            self._active_rounds.pop(telegram_user_id, None)
            return replace(round_state)

    async def get_active_round(self, telegram_user_id: int) -> RocketRound | None:
        async with self._lock:
            round_state = self._active_rounds.get(telegram_user_id)
            if round_state is None:
                return None
            return replace(round_state)

    def reset_balances(self, telegram_user_id: int) -> tuple[int, float]:
        user = self._repository.set_demo_balance(telegram_user_id, self._default_balance_stars)
        user = self._repository.set_demo_ton_balance(telegram_user_id, self._default_balance_ton)
        return user.demo_balance_stars, user.demo_balance_ton

    def adjust_balance(self, telegram_user_id: int, currency: str, amount: float) -> tuple[int, float]:
        normalized_currency = currency.upper()
        safe_amount = self._normalize_amount(normalized_currency, amount)
        if normalized_currency == "XTR":
            user = self._repository.change_demo_balance(telegram_user_id, int(safe_amount))
        elif normalized_currency == "TON":
            user = self._repository.change_demo_ton_balance(telegram_user_id, safe_amount)
        else:
            raise ValueError("unsupported_currency")
        return user.demo_balance_stars, user.demo_balance_ton

    def get_balances(self, telegram_user_id: int) -> tuple[int, float]:
        user = self._repository.get_user(telegram_user_id)
        if user is None:
            return self._default_balance_stars, self._default_balance_ton
        return user.demo_balance_stars, round(user.demo_balance_ton, 2)

    def get_profile_stats(self, telegram_user_id: int) -> tuple[RocketStatsRecord, list[RocketHistoryRecord]]:
        stats = self._repository.get_rocket_stats(telegram_user_id)
        history = self._repository.list_recent_rocket_history(telegram_user_id)
        return stats, history

    def get_leaderboard(self, limit: int = 10) -> list[LeaderboardEntry]:
        return self._repository.get_rocket_leaderboard(limit=limit)

    def get_auto_cashout(self, telegram_user_id: int, currency: str) -> float | None:
        user = self._repository.get_user(telegram_user_id)
        if user is None:
            return None
        if currency.upper() == "TON":
            return user.auto_cashout_ton
        return user.auto_cashout_xtr

    def set_auto_cashout(self, telegram_user_id: int, currency: str, multiplier: float | None) -> float | None:
        user = self._repository.set_auto_cashout(telegram_user_id, currency, multiplier)
        if currency.upper() == "TON":
            return user.auto_cashout_ton
        return user.auto_cashout_xtr

    def _apply_cashout(self, round_state: RocketRound) -> None:
        round_state.status = "cashed_out"
        round_state.payout_amount = self._normalize_amount(
            round_state.currency,
            round_state.bet_amount * round_state.current_multiplier,
        )
        if round_state.currency == "XTR":
            self._repository.change_demo_balance(round_state.telegram_user_id, int(round_state.payout_amount))
        else:
            self._repository.change_demo_ton_balance(round_state.telegram_user_id, round_state.payout_amount)
        self._record_round(round_state)

    def _record_round(self, round_state: RocketRound) -> None:
        payout_amount = self._normalize_amount(round_state.currency, round_state.payout_amount)
        profit_amount = self._normalize_profit(round_state.currency, payout_amount - round_state.bet_amount)
        self._repository.create_rocket_history(
            telegram_user_id=round_state.telegram_user_id,
            currency=round_state.currency,
            bet_amount=round_state.bet_amount,
            crash_multiplier=round_state.crash_multiplier,
            exit_multiplier=round_state.current_multiplier if round_state.status == "cashed_out" else None,
            payout_amount=payout_amount,
            profit_amount=profit_amount,
            status=round_state.status,
        )

    @staticmethod
    def _generate_crash_multiplier() -> float:
        roll = random.random()
        if roll < 0.45:
            return round(random.uniform(1.05, 1.9), 2)
        if roll < 0.8:
            return round(random.uniform(2.0, 3.8), 2)
        if roll < 0.95:
            return round(random.uniform(4.0, 8.5), 2)
        return round(random.uniform(9.0, 20.0), 2)

    @staticmethod
    def _calculate_multiplier(created_monotonic: float) -> float:
        elapsed = max(time.monotonic() - created_monotonic, 0)
        multiplier = 1 + (elapsed * 0.42) + ((elapsed**1.45) * 0.08)
        return round(multiplier, 2)

    @staticmethod
    def _normalize_amount(currency: str, amount: float) -> float:
        if currency == "XTR":
            return max(int(round(amount)), 0)
        return round(max(amount, 0), 2)

    @staticmethod
    def _normalize_profit(currency: str, amount: float) -> float:
        if currency == "XTR":
            return int(round(amount))
        return round(amount, 2)
