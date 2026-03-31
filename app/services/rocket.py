from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass

from app.services.repository import (
    LeaderboardEntry,
    ReferralEntry,
    Repository,
    RocketHistoryRecord,
    RocketStatsRecord,
    WalletTransactionRecord,
)


@dataclass(slots=True)
class RocketBetSlot:
    slot_index: int
    bet_amount: float
    auto_cashout_multiplier: float | None
    current_multiplier: float
    status: str
    payout_amount: float


@dataclass(slots=True)
class RocketRound:
    telegram_user_id: int
    currency: str
    crash_multiplier: float
    current_multiplier: float
    status: str
    created_monotonic: float
    slots: list[RocketBetSlot]


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
        bet_amount: float | None = None,
        auto_cashout_multiplier: float | None = None,
        slots: list[dict] | None = None,
    ) -> RocketRound:
        normalized_currency = currency.upper()
        slot_payloads = self._normalize_slots(normalized_currency, bet_amount, auto_cashout_multiplier, slots)

        async with self._lock:
            if telegram_user_id in self._active_rounds:
                raise ValueError("active_round")

            user = self._repository.get_user(telegram_user_id)
            if user is None:
                raise ValueError("user_not_found")

            total_bet = sum(slot["bet_amount"] for slot in slot_payloads)
            if normalized_currency == "XTR":
                if total_bet > user.demo_balance_stars:
                    raise ValueError("insufficient_balance")
                updated_user = self._repository.change_demo_balance(telegram_user_id, -int(total_bet))
            elif normalized_currency == "TON":
                if total_bet > user.demo_balance_ton:
                    raise ValueError("insufficient_balance")
                updated_user = self._repository.change_demo_ton_balance(telegram_user_id, -total_bet)
            else:
                raise ValueError("unsupported_currency")

            self._repository.create_wallet_transaction(
                telegram_user_id=telegram_user_id,
                action="bet_open",
                currency=normalized_currency,
                amount=-total_bet,
                balance_after=updated_user.demo_balance_stars if normalized_currency == "XTR" else updated_user.demo_balance_ton,
                note=f"Opened {len(slot_payloads)} bet slot(s)",
            )

            round_state = RocketRound(
                telegram_user_id=telegram_user_id,
                currency=normalized_currency,
                crash_multiplier=self._generate_crash_multiplier(),
                current_multiplier=1.00,
                status="flying",
                created_monotonic=time.monotonic(),
                slots=[
                    RocketBetSlot(
                        slot_index=index,
                        bet_amount=slot["bet_amount"],
                        auto_cashout_multiplier=slot["auto_cashout_multiplier"],
                        current_multiplier=1.00,
                        status="flying",
                        payout_amount=0,
                    )
                    for index, slot in enumerate(slot_payloads, start=1)
                ],
            )
            self._active_rounds[telegram_user_id] = round_state
            return self._clone_round(round_state)

    async def tick_round(self, telegram_user_id: int) -> RocketRound | None:
        async with self._lock:
            round_state = self._active_rounds.get(telegram_user_id)
            if round_state is None:
                return None

            multiplier = self._calculate_multiplier(round_state.created_monotonic)
            round_state.current_multiplier = min(multiplier, round_state.crash_multiplier)

            if multiplier >= round_state.crash_multiplier:
                self._crash_remaining_slots(round_state)
                self._active_rounds.pop(telegram_user_id, None)
                return self._clone_round(round_state)

            any_active = False
            for slot in round_state.slots:
                if slot.status != "flying":
                    continue
                any_active = True
                slot.current_multiplier = multiplier
                if slot.auto_cashout_multiplier is not None and multiplier >= slot.auto_cashout_multiplier:
                    self._apply_slot_cashout(round_state, slot)

            if not any(slot.status == "flying" for slot in round_state.slots):
                round_state.status = "finished"
                self._active_rounds.pop(telegram_user_id, None)

            return self._clone_round(round_state)

    async def cash_out(self, telegram_user_id: int, slot_index: int | None = None) -> RocketRound | None:
        async with self._lock:
            round_state = self._active_rounds.get(telegram_user_id)
            if round_state is None:
                return None

            multiplier = self._calculate_multiplier(round_state.created_monotonic)
            round_state.current_multiplier = min(multiplier, round_state.crash_multiplier)

            if multiplier >= round_state.crash_multiplier:
                self._crash_remaining_slots(round_state)
                self._active_rounds.pop(telegram_user_id, None)
                return self._clone_round(round_state)

            target_slot = self._resolve_slot(round_state, slot_index)
            if target_slot is None:
                raise ValueError("slot_not_available")

            target_slot.current_multiplier = multiplier
            self._apply_slot_cashout(round_state, target_slot)

            if not any(slot.status == "flying" for slot in round_state.slots):
                round_state.status = "finished"
                self._active_rounds.pop(telegram_user_id, None)

            return self._clone_round(round_state)

    async def get_active_round(self, telegram_user_id: int) -> RocketRound | None:
        async with self._lock:
            round_state = self._active_rounds.get(telegram_user_id)
            if round_state is None:
                return None
            return self._clone_round(round_state)

    def reset_balances(self, telegram_user_id: int) -> tuple[int, float]:
        user = self._repository.set_demo_balance(telegram_user_id, self._default_balance_stars)
        user = self._repository.set_demo_ton_balance(telegram_user_id, self._default_balance_ton)
        self._repository.create_wallet_transaction(
            telegram_user_id=telegram_user_id,
            action="wallet_reset",
            currency="XTR",
            amount=self._default_balance_stars,
            balance_after=user.demo_balance_stars,
            note="Reset Stars demo balance",
        )
        self._repository.create_wallet_transaction(
            telegram_user_id=telegram_user_id,
            action="wallet_reset",
            currency="TON",
            amount=self._default_balance_ton,
            balance_after=user.demo_balance_ton,
            note="Reset TON demo balance",
        )
        return user.demo_balance_stars, user.demo_balance_ton

    def adjust_balance(self, telegram_user_id: int, currency: str, amount: float, action: str = "wallet_adjust") -> tuple[int, float]:
        normalized_currency = currency.upper()
        safe_amount = self._normalize_amount(normalized_currency, amount)
        if normalized_currency == "XTR":
            user = self._repository.change_demo_balance(telegram_user_id, int(safe_amount))
            self._repository.create_wallet_transaction(
                telegram_user_id=telegram_user_id,
                action=action,
                currency=normalized_currency,
                amount=safe_amount,
                balance_after=user.demo_balance_stars,
                note="Wallet operation",
            )
        elif normalized_currency == "TON":
            user = self._repository.change_demo_ton_balance(telegram_user_id, safe_amount)
            self._repository.create_wallet_transaction(
                telegram_user_id=telegram_user_id,
                action=action,
                currency=normalized_currency,
                amount=safe_amount,
                balance_after=user.demo_balance_ton,
                note="Wallet operation",
            )
        else:
            raise ValueError("unsupported_currency")
        return user.demo_balance_stars, round(user.demo_balance_ton, 2)

    def get_balances(self, telegram_user_id: int) -> tuple[int, float]:
        user = self._repository.get_user(telegram_user_id)
        if user is None:
            return self._default_balance_stars, self._default_balance_ton
        return user.demo_balance_stars, round(user.demo_balance_ton, 2)

    def get_profile_stats(self, telegram_user_id: int) -> tuple[RocketStatsRecord, list[RocketHistoryRecord]]:
        stats = self._repository.get_rocket_stats(telegram_user_id)
        history = self._repository.list_recent_rocket_history(telegram_user_id)
        return stats, history

    def get_wallet_transactions(self, telegram_user_id: int) -> list[WalletTransactionRecord]:
        return self._repository.list_wallet_transactions(telegram_user_id)

    def get_referrals(self, telegram_user_id: int) -> list[ReferralEntry]:
        return self._repository.list_referrals(telegram_user_id)

    def activate_referral_code(self, telegram_user_id: int, referral_code: str) -> ReferralEntry | None:
        normalized = referral_code.strip().upper()
        if not normalized.startswith("ROCKET"):
            raise ValueError("invalid_referral_code")
        try:
            referrer_user_id = int(normalized.removeprefix("ROCKET"))
        except ValueError as exc:
            raise ValueError("invalid_referral_code") from exc
        return self._repository.attach_referral(referrer_user_id, telegram_user_id)

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

    def _normalize_slots(
        self,
        currency: str,
        bet_amount: float | None,
        auto_cashout_multiplier: float | None,
        slots: list[dict] | None,
    ) -> list[dict[str, float | None]]:
        if slots:
            normalized_slots: list[dict[str, float | None]] = []
            for raw_slot in slots[:2]:
                raw_bet = float(raw_slot.get("bet_amount", 0))
                if raw_bet <= 0:
                    continue
                safe_bet = self._normalize_amount(currency, raw_bet)
                safe_auto = raw_slot.get("auto_cashout_multiplier")
                safe_auto_value = round(float(safe_auto), 2) if safe_auto not in {None, ""} else None
                self._validate_slot(currency, safe_bet, safe_auto_value)
                normalized_slots.append(
                    {
                        "bet_amount": safe_bet,
                        "auto_cashout_multiplier": safe_auto_value,
                    }
                )
            if normalized_slots:
                return normalized_slots

        fallback_bet = self._normalize_amount(currency, float(bet_amount or 0))
        fallback_auto = round(auto_cashout_multiplier, 2) if auto_cashout_multiplier is not None else None
        self._validate_slot(currency, fallback_bet, fallback_auto)
        return [{"bet_amount": fallback_bet, "auto_cashout_multiplier": fallback_auto}]

    def _validate_slot(self, currency: str, bet_amount: float, auto_cashout_multiplier: float | None) -> None:
        if auto_cashout_multiplier is not None and auto_cashout_multiplier <= 1.0:
            raise ValueError("invalid_auto_cashout")
        if currency == "XTR" and bet_amount < self._min_bet_stars:
            raise ValueError("bet_too_small")
        if currency == "TON" and bet_amount < self._min_bet_ton:
            raise ValueError("bet_too_small")

    def _resolve_slot(self, round_state: RocketRound, slot_index: int | None) -> RocketBetSlot | None:
        if slot_index is None:
            return next((slot for slot in round_state.slots if slot.status == "flying"), None)
        return next((slot for slot in round_state.slots if slot.slot_index == slot_index and slot.status == "flying"), None)

    def _apply_slot_cashout(self, round_state: RocketRound, slot: RocketBetSlot) -> None:
        slot.status = "cashed_out"
        slot.payout_amount = self._normalize_amount(round_state.currency, slot.bet_amount * round_state.current_multiplier)
        slot.current_multiplier = round_state.current_multiplier
        if round_state.currency == "XTR":
            updated_user = self._repository.change_demo_balance(round_state.telegram_user_id, int(slot.payout_amount))
            balance_after = updated_user.demo_balance_stars
        else:
            updated_user = self._repository.change_demo_ton_balance(round_state.telegram_user_id, slot.payout_amount)
            balance_after = updated_user.demo_balance_ton

        self._repository.create_wallet_transaction(
            telegram_user_id=round_state.telegram_user_id,
            action="cashout",
            currency=round_state.currency,
            amount=slot.payout_amount,
            balance_after=balance_after,
            note=f"Cashout for slot {slot.slot_index}",
        )
        self._record_slot(round_state, slot)

    def _crash_remaining_slots(self, round_state: RocketRound) -> None:
        round_state.current_multiplier = round_state.crash_multiplier
        for slot in round_state.slots:
            if slot.status != "flying":
                continue
            slot.status = "crashed"
            slot.current_multiplier = round_state.crash_multiplier
            slot.payout_amount = 0
            self._record_slot(round_state, slot)
        round_state.status = "crashed"

    def _record_slot(self, round_state: RocketRound, slot: RocketBetSlot) -> None:
        payout_amount = self._normalize_amount(round_state.currency, slot.payout_amount)
        profit_amount = self._normalize_profit(round_state.currency, payout_amount - slot.bet_amount)
        self._repository.create_rocket_history(
            telegram_user_id=round_state.telegram_user_id,
            slot_index=slot.slot_index,
            currency=round_state.currency,
            bet_amount=slot.bet_amount,
            crash_multiplier=round_state.crash_multiplier,
            exit_multiplier=slot.current_multiplier if slot.status == "cashed_out" else None,
            payout_amount=payout_amount,
            profit_amount=profit_amount,
            status=slot.status,
        )

    def _clone_round(self, round_state: RocketRound) -> RocketRound:
        return RocketRound(
            telegram_user_id=round_state.telegram_user_id,
            currency=round_state.currency,
            crash_multiplier=round_state.crash_multiplier,
            current_multiplier=round_state.current_multiplier,
            status=round_state.status,
            created_monotonic=round_state.created_monotonic,
            slots=[
                RocketBetSlot(
                    slot_index=slot.slot_index,
                    bet_amount=slot.bet_amount,
                    auto_cashout_multiplier=slot.auto_cashout_multiplier,
                    current_multiplier=slot.current_multiplier,
                    status=slot.status,
                    payout_amount=slot.payout_amount,
                )
                for slot in round_state.slots
            ],
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
