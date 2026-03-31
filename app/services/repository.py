from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Iterator


@dataclass(slots=True)
class UserRecord:
    telegram_user_id: int
    username: str | None
    first_name: str | None
    plan: str
    demo_balance_stars: int
    demo_balance_ton: float
    auto_cashout_xtr: float | None
    auto_cashout_ton: float | None
    daily_budget_queries: int
    usage_date: str
    created_at: str
    updated_at: str


@dataclass(slots=True)
class SubscriptionRecord:
    id: int
    telegram_user_id: int
    plan: str
    status: str
    provider: str
    started_at: str
    expires_at: str | None
    created_at: str


@dataclass(slots=True)
class PaymentRecord:
    id: int
    telegram_user_id: int
    product_code: str
    amount_stars: int
    currency: str
    provider: str
    status: str
    checkout_url: str | None
    created_at: str


@dataclass(slots=True)
class MarketSnapshotRecord:
    id: int
    gift_slug: str
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
    source_name: str
    updated_at: str


@dataclass(slots=True)
class PortfolioItemRecord:
    id: int
    telegram_user_id: int
    gift_slug: str
    quantity: int
    buy_price_stars: int
    created_at: str


@dataclass(slots=True)
class AlertRecord:
    id: int
    telegram_user_id: int
    alert_type: str
    budget_max: int | None
    discount_min_pct: float | None
    status: str
    created_at: str


@dataclass(slots=True)
class RocketHistoryRecord:
    id: int
    telegram_user_id: int
    slot_index: int
    currency: str
    bet_amount: float
    crash_multiplier: float
    exit_multiplier: float | None
    payout_amount: float
    profit_amount: float
    status: str
    created_at: str


@dataclass(slots=True)
class RocketStatsRecord:
    rounds_total: int
    wins_total: int
    losses_total: int
    total_wagered_stars: int
    total_payout_stars: int
    total_profit_stars: int
    total_wagered_ton: float
    total_payout_ton: float
    total_profit_ton: float
    best_multiplier: float


@dataclass(slots=True)
class LeaderboardEntry:
    telegram_user_id: int
    username: str | None
    first_name: str | None
    rounds_total: int
    wins_total: int
    total_profit_stars: int
    total_profit_ton: float
    best_multiplier: float


@dataclass(slots=True)
class WalletTransactionRecord:
    id: int
    telegram_user_id: int
    action: str
    currency: str
    amount: float
    balance_after: float
    note: str
    created_at: str


@dataclass(slots=True)
class ReferralEntry:
    id: int
    referrer_user_id: int
    invited_user_id: int
    invited_name: str | None
    bonus_stars: int
    bonus_ton: float
    created_at: str


class Repository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    telegram_user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    plan TEXT NOT NULL DEFAULT 'free',
                    demo_balance_stars INTEGER NOT NULL DEFAULT 10000,
                    demo_balance_ton REAL NOT NULL DEFAULT 25,
                    auto_cashout_xtr REAL,
                    auto_cashout_ton REAL,
                    daily_budget_queries INTEGER NOT NULL DEFAULT 0,
                    usage_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    plan TEXT NOT NULL,
                    status TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    expires_at TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    product_code TEXT NOT NULL,
                    amount_stars INTEGER NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'XTR',
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL,
                    checkout_url TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS market_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gift_slug TEXT NOT NULL,
                    title TEXT NOT NULL,
                    model TEXT NOT NULL DEFAULT '',
                    backdrop TEXT NOT NULL DEFAULT '',
                    image_url TEXT NOT NULL DEFAULT '',
                    image_path TEXT NOT NULL DEFAULT '',
                    price_stars INTEGER NOT NULL,
                    price_ton REAL NOT NULL DEFAULT 0,
                    median_stars INTEGER NOT NULL,
                    median_ton REAL NOT NULL DEFAULT 0,
                    liquidity TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    comment TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS portfolio_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    gift_slug TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    buy_price_stars INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    alert_type TEXT NOT NULL,
                    budget_max INTEGER,
                    discount_min_pct REAL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rocket_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    slot_index INTEGER NOT NULL DEFAULT 1,
                    currency TEXT NOT NULL,
                    bet_amount REAL NOT NULL,
                    crash_multiplier REAL NOT NULL,
                    exit_multiplier REAL,
                    payout_amount REAL NOT NULL DEFAULT 0,
                    profit_amount REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS wallet_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    amount REAL NOT NULL,
                    balance_after REAL NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_user_id INTEGER NOT NULL,
                    invited_user_id INTEGER NOT NULL UNIQUE,
                    bonus_stars INTEGER NOT NULL DEFAULT 0,
                    bonus_ton REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )

            columns = {row["name"] for row in conn.execute("PRAGMA table_info(market_snapshots)").fetchall()}
            if "model" not in columns:
                conn.execute("ALTER TABLE market_snapshots ADD COLUMN model TEXT NOT NULL DEFAULT ''")
            if "backdrop" not in columns:
                conn.execute("ALTER TABLE market_snapshots ADD COLUMN backdrop TEXT NOT NULL DEFAULT ''")
            if "image_url" not in columns:
                conn.execute("ALTER TABLE market_snapshots ADD COLUMN image_url TEXT NOT NULL DEFAULT ''")
            if "image_path" not in columns:
                conn.execute("ALTER TABLE market_snapshots ADD COLUMN image_path TEXT NOT NULL DEFAULT ''")
            if "price_ton" not in columns:
                conn.execute("ALTER TABLE market_snapshots ADD COLUMN price_ton REAL NOT NULL DEFAULT 0")
            if "median_ton" not in columns:
                conn.execute("ALTER TABLE market_snapshots ADD COLUMN median_ton REAL NOT NULL DEFAULT 0")

            user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
            if "demo_balance_stars" not in user_columns:
                conn.execute("ALTER TABLE users ADD COLUMN demo_balance_stars INTEGER NOT NULL DEFAULT 10000")
            if "demo_balance_ton" not in user_columns:
                conn.execute("ALTER TABLE users ADD COLUMN demo_balance_ton REAL NOT NULL DEFAULT 25")
            if "auto_cashout_xtr" not in user_columns:
                conn.execute("ALTER TABLE users ADD COLUMN auto_cashout_xtr REAL")
            if "auto_cashout_ton" not in user_columns:
                conn.execute("ALTER TABLE users ADD COLUMN auto_cashout_ton REAL")

            rocket_columns = {row["name"] for row in conn.execute("PRAGMA table_info(rocket_history)").fetchall()}
            if "slot_index" not in rocket_columns:
                conn.execute("ALTER TABLE rocket_history ADD COLUMN slot_index INTEGER NOT NULL DEFAULT 1")

    def get_or_create_user(self, telegram_user_id: int, username: str | None, first_name: str | None) -> UserRecord:
        existing = self.get_user(telegram_user_id)
        if existing is not None:
            self._refresh_user_profile(telegram_user_id, username, first_name)
            return self.get_user(telegram_user_id)  # type: ignore[return-value]

        now = self._utc_now_iso()
        today = self._today_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    telegram_user_id, username, first_name, plan, demo_balance_stars, demo_balance_ton,
                    auto_cashout_xtr, auto_cashout_ton, daily_budget_queries, usage_date, created_at, updated_at
                )
                VALUES (?, ?, ?, 'free', 10000, 25, NULL, NULL, 0, ?, ?, ?)
                """,
                (telegram_user_id, username, first_name, today, now, now),
            )
        return self.get_user(telegram_user_id)  # type: ignore[return-value]

    def get_user(self, telegram_user_id: int) -> UserRecord | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE telegram_user_id = ?", (telegram_user_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_user(row)

    def bump_budget_query(self, telegram_user_id: int) -> UserRecord:
        self.reset_usage_if_needed(telegram_user_id)
        now = self._utc_now_iso()
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET daily_budget_queries = daily_budget_queries + 1, updated_at = ? WHERE telegram_user_id = ?",
                (now, telegram_user_id),
            )
            conn.execute(
                "INSERT INTO usage_logs (telegram_user_id, action, created_at) VALUES (?, 'budget_query', ?)",
                (telegram_user_id, now),
            )
        return self.get_user(telegram_user_id)  # type: ignore[return-value]

    def set_plan(self, telegram_user_id: int, plan: str) -> UserRecord:
        now = self._utc_now_iso()
        with self.connect() as conn:
            conn.execute("UPDATE users SET plan = ?, updated_at = ? WHERE telegram_user_id = ?", (plan, now, telegram_user_id))
            conn.execute(
                "INSERT INTO usage_logs (telegram_user_id, action, created_at) VALUES (?, ?, ?)",
                (telegram_user_id, f"set_plan:{plan}", now),
            )
        return self.get_user(telegram_user_id)  # type: ignore[return-value]

    def change_demo_balance(self, telegram_user_id: int, delta_stars: int) -> UserRecord:
        now = self._utc_now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET demo_balance_stars = MAX(demo_balance_stars + ?, 0),
                    updated_at = ?
                WHERE telegram_user_id = ?
                """,
                (delta_stars, now, telegram_user_id),
            )
            conn.execute(
                "INSERT INTO usage_logs (telegram_user_id, action, created_at) VALUES (?, ?, ?)",
                (telegram_user_id, f"balance:{delta_stars:+}", now),
            )
        return self.get_user(telegram_user_id)  # type: ignore[return-value]

    def change_demo_ton_balance(self, telegram_user_id: int, delta_ton: float) -> UserRecord:
        now = self._utc_now_iso()
        safe_delta = round(delta_ton, 4)
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET demo_balance_ton = MAX(demo_balance_ton + ?, 0),
                    updated_at = ?
                WHERE telegram_user_id = ?
                """,
                (safe_delta, now, telegram_user_id),
            )
            conn.execute(
                "INSERT INTO usage_logs (telegram_user_id, action, created_at) VALUES (?, ?, ?)",
                (telegram_user_id, f"balance_ton:{safe_delta:+.4f}", now),
            )
        return self.get_user(telegram_user_id)  # type: ignore[return-value]

    def set_demo_balance(self, telegram_user_id: int, amount_stars: int) -> UserRecord:
        now = self._utc_now_iso()
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET demo_balance_stars = ?, updated_at = ? WHERE telegram_user_id = ?",
                (max(amount_stars, 0), now, telegram_user_id),
            )
            conn.execute(
                "INSERT INTO usage_logs (telegram_user_id, action, created_at) VALUES (?, ?, ?)",
                (telegram_user_id, f"balance:set:{max(amount_stars, 0)}", now),
            )
        return self.get_user(telegram_user_id)  # type: ignore[return-value]

    def set_demo_ton_balance(self, telegram_user_id: int, amount_ton: float) -> UserRecord:
        now = self._utc_now_iso()
        safe_amount = round(max(amount_ton, 0), 4)
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET demo_balance_ton = ?, updated_at = ? WHERE telegram_user_id = ?",
                (safe_amount, now, telegram_user_id),
            )
            conn.execute(
                "INSERT INTO usage_logs (telegram_user_id, action, created_at) VALUES (?, ?, ?)",
                (telegram_user_id, f"balance_ton:set:{safe_amount:.4f}", now),
            )
        return self.get_user(telegram_user_id)  # type: ignore[return-value]

    def set_auto_cashout(self, telegram_user_id: int, currency: str, multiplier: float | None) -> UserRecord:
        now = self._utc_now_iso()
        column_name = "auto_cashout_xtr" if currency.upper() == "XTR" else "auto_cashout_ton"
        safe_multiplier = round(multiplier, 2) if multiplier is not None else None
        with self.connect() as conn:
            conn.execute(
                f"UPDATE users SET {column_name} = ?, updated_at = ? WHERE telegram_user_id = ?",
                (safe_multiplier, now, telegram_user_id),
            )
            action_value = "off" if safe_multiplier is None else f"{safe_multiplier:.2f}"
            conn.execute(
                "INSERT INTO usage_logs (telegram_user_id, action, created_at) VALUES (?, ?, ?)",
                (telegram_user_id, f"auto_cashout:{currency.lower()}:{action_value}", now),
            )
        return self.get_user(telegram_user_id)  # type: ignore[return-value]

    def create_rocket_history(
        self,
        telegram_user_id: int,
        slot_index: int,
        currency: str,
        bet_amount: float,
        crash_multiplier: float,
        exit_multiplier: float | None,
        payout_amount: float,
        profit_amount: float,
        status: str,
    ) -> RocketHistoryRecord:
        now = self._utc_now_iso()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO rocket_history (
                    telegram_user_id, slot_index, currency, bet_amount, crash_multiplier, exit_multiplier,
                    payout_amount, profit_amount, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    telegram_user_id,
                    slot_index,
                    currency,
                    bet_amount,
                    crash_multiplier,
                    exit_multiplier,
                    payout_amount,
                    profit_amount,
                    status,
                    now,
                ),
            )
            history_id = cursor.lastrowid
        return self.get_rocket_history(history_id)  # type: ignore[arg-type]

    def get_rocket_history(self, history_id: int) -> RocketHistoryRecord | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM rocket_history WHERE id = ?", (history_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_rocket_history(row)

    def list_recent_rocket_history(self, telegram_user_id: int, limit: int = 8) -> list[RocketHistoryRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM rocket_history WHERE telegram_user_id = ? ORDER BY id DESC LIMIT ?",
                (telegram_user_id, limit),
            ).fetchall()
        return [self._row_to_rocket_history(row) for row in rows]

    def get_rocket_stats(self, telegram_user_id: int) -> RocketStatsRecord:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS rounds_total,
                    SUM(CASE WHEN status = 'cashed_out' THEN 1 ELSE 0 END) AS wins_total,
                    SUM(CASE WHEN status = 'crashed' THEN 1 ELSE 0 END) AS losses_total,
                    SUM(CASE WHEN currency = 'XTR' THEN bet_amount ELSE 0 END) AS total_wagered_stars,
                    SUM(CASE WHEN currency = 'XTR' THEN payout_amount ELSE 0 END) AS total_payout_stars,
                    SUM(CASE WHEN currency = 'XTR' THEN profit_amount ELSE 0 END) AS total_profit_stars,
                    SUM(CASE WHEN currency = 'TON' THEN bet_amount ELSE 0 END) AS total_wagered_ton,
                    SUM(CASE WHEN currency = 'TON' THEN payout_amount ELSE 0 END) AS total_payout_ton,
                    SUM(CASE WHEN currency = 'TON' THEN profit_amount ELSE 0 END) AS total_profit_ton,
                    MAX(COALESCE(exit_multiplier, crash_multiplier, 0)) AS best_multiplier
                FROM rocket_history
                WHERE telegram_user_id = ?
                """,
                (telegram_user_id,),
            ).fetchone()
        return RocketStatsRecord(
            rounds_total=int(row["rounds_total"] or 0),
            wins_total=int(row["wins_total"] or 0),
            losses_total=int(row["losses_total"] or 0),
            total_wagered_stars=int(round(row["total_wagered_stars"] or 0)),
            total_payout_stars=int(round(row["total_payout_stars"] or 0)),
            total_profit_stars=int(round(row["total_profit_stars"] or 0)),
            total_wagered_ton=round(float(row["total_wagered_ton"] or 0), 2),
            total_payout_ton=round(float(row["total_payout_ton"] or 0), 2),
            total_profit_ton=round(float(row["total_profit_ton"] or 0), 2),
            best_multiplier=round(float(row["best_multiplier"] or 0), 2),
        )

    def get_rocket_leaderboard(self, limit: int = 10) -> list[LeaderboardEntry]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    u.telegram_user_id AS telegram_user_id,
                    u.username AS username,
                    u.first_name AS first_name,
                    COUNT(r.id) AS rounds_total,
                    SUM(CASE WHEN r.status = 'cashed_out' THEN 1 ELSE 0 END) AS wins_total,
                    SUM(CASE WHEN r.currency = 'XTR' THEN r.profit_amount ELSE 0 END) AS total_profit_stars,
                    SUM(CASE WHEN r.currency = 'TON' THEN r.profit_amount ELSE 0 END) AS total_profit_ton,
                    MAX(COALESCE(r.exit_multiplier, r.crash_multiplier, 0)) AS best_multiplier
                FROM users u
                JOIN rocket_history r ON r.telegram_user_id = u.telegram_user_id
                GROUP BY u.telegram_user_id, u.username, u.first_name
                ORDER BY total_profit_stars DESC, total_profit_ton DESC, best_multiplier DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            LeaderboardEntry(
                telegram_user_id=row["telegram_user_id"],
                username=row["username"],
                first_name=row["first_name"],
                rounds_total=int(row["rounds_total"] or 0),
                wins_total=int(row["wins_total"] or 0),
                total_profit_stars=int(round(row["total_profit_stars"] or 0)),
                total_profit_ton=round(float(row["total_profit_ton"] or 0), 2),
                best_multiplier=round(float(row["best_multiplier"] or 0), 2),
            )
            for row in rows
        ]

    def create_wallet_transaction(
        self,
        telegram_user_id: int,
        action: str,
        currency: str,
        amount: float,
        balance_after: float,
        note: str = "",
    ) -> WalletTransactionRecord:
        now = self._utc_now_iso()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO wallet_transactions (
                    telegram_user_id, action, currency, amount, balance_after, note, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    telegram_user_id,
                    action,
                    currency.upper(),
                    amount,
                    balance_after,
                    note,
                    now,
                ),
            )
            transaction_id = cursor.lastrowid
        return self.get_wallet_transaction(transaction_id)  # type: ignore[arg-type]

    def get_wallet_transaction(self, transaction_id: int) -> WalletTransactionRecord | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM wallet_transactions WHERE id = ?", (transaction_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_wallet_transaction(row)

    def list_wallet_transactions(self, telegram_user_id: int, limit: int = 12) -> list[WalletTransactionRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM wallet_transactions
                WHERE telegram_user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (telegram_user_id, limit),
            ).fetchall()
        return [self._row_to_wallet_transaction(row) for row in rows]

    def attach_referral(self, referrer_user_id: int, invited_user_id: int) -> ReferralEntry | None:
        if referrer_user_id == invited_user_id:
            return None
        existing = self.get_referral_by_invited(invited_user_id)
        if existing is not None:
            return existing

        now = self._utc_now_iso()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO referrals (
                    referrer_user_id, invited_user_id, bonus_stars, bonus_ton, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (referrer_user_id, invited_user_id, 300, 0.15, now),
            )
            referral_id = cursor.lastrowid
        if not referral_id:
            return self.get_referral_by_invited(invited_user_id)

        referrer = self.get_user(referrer_user_id)
        if referrer is not None:
            self.change_demo_balance(referrer_user_id, 300)
            self.change_demo_ton_balance(referrer_user_id, 0.15)
            updated = self.get_user(referrer_user_id)
            if updated is not None:
                self.create_wallet_transaction(
                    telegram_user_id=referrer_user_id,
                    action="referral_bonus",
                    currency="XTR",
                    amount=300,
                    balance_after=updated.demo_balance_stars,
                    note=f"Bonus for invited user #{invited_user_id}",
                )
                self.create_wallet_transaction(
                    telegram_user_id=referrer_user_id,
                    action="referral_bonus",
                    currency="TON",
                    amount=0.15,
                    balance_after=updated.demo_balance_ton,
                    note=f"Bonus for invited user #{invited_user_id}",
                )
        return self.get_referral(referral_id)

    def get_referral(self, referral_id: int) -> ReferralEntry | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    r.*,
                    COALESCE(u.first_name, u.username, 'Player') AS invited_name
                FROM referrals r
                LEFT JOIN users u ON u.telegram_user_id = r.invited_user_id
                WHERE r.id = ?
                """,
                (referral_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_referral(row)

    def get_referral_by_invited(self, invited_user_id: int) -> ReferralEntry | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    r.*,
                    COALESCE(u.first_name, u.username, 'Player') AS invited_name
                FROM referrals r
                LEFT JOIN users u ON u.telegram_user_id = r.invited_user_id
                WHERE r.invited_user_id = ?
                """,
                (invited_user_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_referral(row)

    def list_referrals(self, referrer_user_id: int, limit: int = 12) -> list[ReferralEntry]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    r.*,
                    COALESCE(u.first_name, u.username, 'Player') AS invited_name
                FROM referrals r
                LEFT JOIN users u ON u.telegram_user_id = r.invited_user_id
                WHERE r.referrer_user_id = ?
                ORDER BY r.id DESC
                LIMIT ?
                """,
                (referrer_user_id, limit),
            ).fetchall()
        return [self._row_to_referral(row) for row in rows]

    def create_payment(
        self,
        telegram_user_id: int,
        product_code: str,
        amount_stars: int,
        provider: str,
        status: str,
        checkout_url: str | None,
    ) -> PaymentRecord:
        now = self._utc_now_iso()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO payments (
                    telegram_user_id, product_code, amount_stars,
                    currency, provider, status, checkout_url, created_at
                )
                VALUES (?, ?, ?, 'XTR', ?, ?, ?, ?)
                """,
                (telegram_user_id, product_code, amount_stars, provider, status, checkout_url, now),
            )
            payment_id = cursor.lastrowid
        return self.get_payment(payment_id)  # type: ignore[arg-type]

    def get_payment(self, payment_id: int) -> PaymentRecord | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
        if row is None:
            return None
        return PaymentRecord(
            id=row["id"],
            telegram_user_id=row["telegram_user_id"],
            product_code=row["product_code"],
            amount_stars=row["amount_stars"],
            currency=row["currency"],
            provider=row["provider"],
            status=row["status"],
            checkout_url=row["checkout_url"],
            created_at=row["created_at"],
        )

    def activate_subscription(self, telegram_user_id: int, plan: str, provider: str) -> SubscriptionRecord:
        now = self._utc_now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO subscriptions (
                    telegram_user_id, plan, status, provider, started_at, expires_at, created_at
                )
                VALUES (?, ?, 'active', ?, ?, NULL, ?)
                """,
                (telegram_user_id, plan, provider, now, now),
            )
            subscription_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        self.set_plan(telegram_user_id, plan)
        return self.get_subscription(subscription_id)  # type: ignore[arg-type]

    def get_latest_subscription(self, telegram_user_id: int) -> SubscriptionRecord | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM subscriptions WHERE telegram_user_id = ? ORDER BY id DESC LIMIT 1",
                (telegram_user_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_subscription(row)

    def get_subscription(self, subscription_id: int) -> SubscriptionRecord | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM subscriptions WHERE id = ?", (subscription_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_subscription(row)

    def seed_market_snapshots(self) -> None:
        now = self._utc_now_iso()
        rows = [
            {"gift_slug": "plush-pepe-221", "title": "Plush Pepe #221", "model": "Pepe Plush", "backdrop": "Neon Mint", "image_url": "https://placehold.co/600x600/png?text=Plush+Pepe", "image_path": "", "price_stars": 2780, "price_ton": 2.8, "median_stars": 3190, "median_ton": 3.2, "liquidity": "high", "risk": "low", "comment": "Цена ниже медианы, рынок активный, хороший вход для осторожного сценария.", "source_name": "demo_market_feed", "updated_at": now},
            {"gift_slug": "golden-cat-88", "title": "Golden Cat #88", "model": "Golden Cat", "backdrop": "Amber Gold", "image_url": "https://placehold.co/600x600/png?text=Golden+Cat", "image_path": "", "price_stars": 4920, "price_ton": 4.9, "median_stars": 5480, "median_ton": 5.5, "liquidity": "medium", "risk": "medium", "comment": "Есть дисконт и потенциал роста, но ликвидность ниже, чем у лидеров.", "source_name": "demo_market_feed", "updated_at": now},
            {"gift_slug": "pixel-heart-14", "title": "Pixel Heart #14", "model": "Pixel Heart", "backdrop": "Candy Sky", "image_url": "https://placehold.co/600x600/png?text=Pixel+Heart", "image_path": "", "price_stars": 1460, "price_ton": 1.5, "median_stars": 1710, "median_ton": 1.7, "liquidity": "high", "risk": "low", "comment": "Подходит для небольшого бюджета и быстрой перепродажи.", "source_name": "demo_market_feed", "updated_at": now},
            {"gift_slug": "crystal-dino-7", "title": "Crystal Dino #7", "model": "Crystal Dino", "backdrop": "Blue Crystal", "image_url": "https://placehold.co/600x600/png?text=Crystal+Dino", "image_path": "", "price_stars": 6890, "price_ton": 6.9, "median_stars": 7520, "median_ton": 7.5, "liquidity": "medium", "risk": "medium", "comment": "Интересный вариант под среднесрочный hold, если нужен более редкий лот.", "source_name": "demo_market_feed", "updated_at": now},
            {"gift_slug": "retro-rocket-301", "title": "Retro Rocket #301", "model": "Retro Rocket", "backdrop": "Sunset Orange", "image_url": "https://placehold.co/600x600/png?text=Retro+Rocket", "image_path": "", "price_stars": 950, "price_ton": 1.0, "median_stars": 1140, "median_ton": 1.1, "liquidity": "medium", "risk": "low", "comment": "Недорогой вход, подходит как первая тестовая покупка.", "source_name": "demo_market_feed", "updated_at": now},
            {"gift_slug": "midnight-owl-52", "title": "Midnight Owl #52", "model": "Midnight Owl", "backdrop": "Night Violet", "image_url": "https://placehold.co/600x600/png?text=Midnight+Owl", "image_path": "", "price_stars": 3540, "price_ton": 3.5, "median_stars": 4010, "median_ton": 4.0, "liquidity": "high", "risk": "low", "comment": "Сильный баланс между ценой входа и ликвидностью.", "source_name": "demo_market_feed", "updated_at": now},
            {"gift_slug": "lava-fox-19", "title": "Lava Fox #19", "model": "Lava Fox", "backdrop": "Molten Red", "image_url": "https://placehold.co/600x600/png?text=Lava+Fox", "image_path": "", "price_stars": 6120, "price_ton": 6.1, "median_stars": 6880, "median_ton": 6.9, "liquidity": "medium", "risk": "medium", "comment": "Интересен, когда нужен более редкий визуал без ухода в слишком высокий риск.", "source_name": "demo_market_feed", "updated_at": now},
            {"gift_slug": "ice-whale-203", "title": "Ice Whale #203", "model": "Ice Whale", "backdrop": "Arctic Blue", "image_url": "https://placehold.co/600x600/png?text=Ice+Whale", "image_path": "", "price_stars": 2280, "price_ton": 2.3, "median_stars": 2570, "median_ton": 2.6, "liquidity": "high", "risk": "low", "comment": "Подходит для спокойной стратегии и короткого удержания.", "source_name": "demo_market_feed", "updated_at": now},
            {"gift_slug": "royal-mask-9", "title": "Royal Mask #9", "model": "Royal Mask", "backdrop": "Velvet Purple", "image_url": "https://placehold.co/600x600/png?text=Royal+Mask", "image_path": "", "price_stars": 8420, "price_ton": 8.4, "median_stars": 9290, "median_ton": 9.3, "liquidity": "medium", "risk": "high", "comment": "Более рискованный вариант, но с потенциалом у премиального сегмента.", "source_name": "demo_market_feed", "updated_at": now},
            {"gift_slug": "forest-orb-144", "title": "Forest Orb #144", "model": "Forest Orb", "backdrop": "Emerald Moss", "image_url": "https://placehold.co/600x600/png?text=Forest+Orb", "image_path": "", "price_stars": 1880, "price_ton": 1.9, "median_stars": 2190, "median_ton": 2.2, "liquidity": "medium", "risk": "low", "comment": "Доступный вход с неплохим дисконтом и понятной ликвидностью.", "source_name": "demo_market_feed", "updated_at": now},
        ]
        self.replace_market_snapshots(rows)

    def replace_market_snapshots(self, rows: list[dict[str, object]]) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM market_snapshots")
            conn.executemany(
                """
                INSERT INTO market_snapshots (
                    gift_slug, title, model, backdrop, image_url, image_path, price_stars, price_ton, median_stars, median_ton,
                    liquidity, risk, comment, source_name, updated_at
                )
                VALUES (
                    :gift_slug, :title, :model, :backdrop, :image_url, :image_path, :price_stars, :price_ton, :median_stars, :median_ton,
                    :liquidity, :risk, :comment, :source_name, :updated_at
                )
                """,
                rows,
            )

    def has_market_snapshots(self) -> bool:
        with self.connect() as conn:
            count = conn.execute("SELECT COUNT(*) AS count FROM market_snapshots").fetchone()["count"]
        return bool(count)

    def list_market_snapshots(self) -> list[MarketSnapshotRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM market_snapshots
                ORDER BY ((median_stars - price_stars) * 1.0 / CASE WHEN median_stars = 0 THEN 1 ELSE median_stars END) DESC, price_stars DESC
                """
            ).fetchall()
        return [self._row_to_market_snapshot(row) for row in rows]

    def get_market_snapshot_by_slug(self, gift_slug: str) -> MarketSnapshotRecord | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM market_snapshots WHERE gift_slug = ? LIMIT 1", (gift_slug,)).fetchone()
        if row is None:
            return None
        return self._row_to_market_snapshot(row)

    def add_portfolio_item(self, telegram_user_id: int, gift_slug: str, buy_price_stars: int, quantity: int = 1) -> PortfolioItemRecord:
        now = self._utc_now_iso()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO portfolio_items (
                    telegram_user_id, gift_slug, quantity, buy_price_stars, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (telegram_user_id, gift_slug, quantity, buy_price_stars, now),
            )
            item_id = cursor.lastrowid
        return self.get_portfolio_item(item_id)  # type: ignore[arg-type]

    def list_portfolio_items(self, telegram_user_id: int) -> list[PortfolioItemRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM portfolio_items WHERE telegram_user_id = ? ORDER BY id DESC",
                (telegram_user_id,),
            ).fetchall()
        return [self._row_to_portfolio_item(row) for row in rows]

    def get_portfolio_item(self, item_id: int) -> PortfolioItemRecord | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM portfolio_items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_portfolio_item(row)

    def create_alert(
        self,
        telegram_user_id: int,
        alert_type: str,
        budget_max: int | None,
        discount_min_pct: float | None,
    ) -> AlertRecord:
        now = self._utc_now_iso()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO alerts (
                    telegram_user_id, alert_type, budget_max, discount_min_pct, status, created_at
                )
                VALUES (?, ?, ?, ?, 'active', ?)
                """,
                (telegram_user_id, alert_type, budget_max, discount_min_pct, now),
            )
            alert_id = cursor.lastrowid
        return self.get_alert(alert_id)  # type: ignore[arg-type]

    def list_alerts(self, telegram_user_id: int) -> list[AlertRecord]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM alerts WHERE telegram_user_id = ? ORDER BY id DESC", (telegram_user_id,)).fetchall()
        return [self._row_to_alert(row) for row in rows]

    def get_alert(self, alert_id: int) -> AlertRecord | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_alert(row)

    def reset_usage_if_needed(self, telegram_user_id: int) -> None:
        user = self.get_user(telegram_user_id)
        if user is None or user.usage_date == self._today_iso():
            return
        now = self._utc_now_iso()
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET daily_budget_queries = 0, usage_date = ?, updated_at = ? WHERE telegram_user_id = ?",
                (self._today_iso(), now, telegram_user_id),
            )

    def _refresh_user_profile(self, telegram_user_id: int, username: str | None, first_name: str | None) -> None:
        now = self._utc_now_iso()
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET username = ?, first_name = ?, updated_at = ? WHERE telegram_user_id = ?",
                (username, first_name, now, telegram_user_id),
            )

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> UserRecord:
        return UserRecord(
            telegram_user_id=row["telegram_user_id"],
            username=row["username"],
            first_name=row["first_name"],
            plan=row["plan"],
            demo_balance_stars=row["demo_balance_stars"],
            demo_balance_ton=row["demo_balance_ton"],
            auto_cashout_xtr=float(row["auto_cashout_xtr"]) if row["auto_cashout_xtr"] is not None else None,
            auto_cashout_ton=float(row["auto_cashout_ton"]) if row["auto_cashout_ton"] is not None else None,
            daily_budget_queries=row["daily_budget_queries"],
            usage_date=row["usage_date"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_subscription(row: sqlite3.Row) -> SubscriptionRecord:
        return SubscriptionRecord(
            id=row["id"],
            telegram_user_id=row["telegram_user_id"],
            plan=row["plan"],
            status=row["status"],
            provider=row["provider"],
            started_at=row["started_at"],
            expires_at=row["expires_at"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_market_snapshot(row: sqlite3.Row) -> MarketSnapshotRecord:
        return MarketSnapshotRecord(
            id=row["id"],
            gift_slug=row["gift_slug"],
            title=row["title"],
            model=row["model"],
            backdrop=row["backdrop"],
            image_url=row["image_url"],
            image_path=row["image_path"],
            price_stars=row["price_stars"],
            price_ton=row["price_ton"],
            median_stars=row["median_stars"],
            median_ton=row["median_ton"],
            liquidity=row["liquidity"],
            risk=row["risk"],
            comment=row["comment"],
            source_name=row["source_name"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_portfolio_item(row: sqlite3.Row) -> PortfolioItemRecord:
        return PortfolioItemRecord(
            id=row["id"],
            telegram_user_id=row["telegram_user_id"],
            gift_slug=row["gift_slug"],
            quantity=row["quantity"],
            buy_price_stars=row["buy_price_stars"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_alert(row: sqlite3.Row) -> AlertRecord:
        return AlertRecord(
            id=row["id"],
            telegram_user_id=row["telegram_user_id"],
            alert_type=row["alert_type"],
            budget_max=row["budget_max"],
            discount_min_pct=row["discount_min_pct"],
            status=row["status"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_rocket_history(row: sqlite3.Row) -> RocketHistoryRecord:
        return RocketHistoryRecord(
            id=row["id"],
            telegram_user_id=row["telegram_user_id"],
            slot_index=int(row["slot_index"] or 1),
            currency=row["currency"],
            bet_amount=float(row["bet_amount"]),
            crash_multiplier=float(row["crash_multiplier"]),
            exit_multiplier=float(row["exit_multiplier"]) if row["exit_multiplier"] is not None else None,
            payout_amount=float(row["payout_amount"]),
            profit_amount=float(row["profit_amount"]),
            status=row["status"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_wallet_transaction(row: sqlite3.Row) -> WalletTransactionRecord:
        return WalletTransactionRecord(
            id=row["id"],
            telegram_user_id=row["telegram_user_id"],
            action=row["action"],
            currency=row["currency"],
            amount=float(row["amount"]),
            balance_after=float(row["balance_after"]),
            note=row["note"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_referral(row: sqlite3.Row) -> ReferralEntry:
        return ReferralEntry(
            id=row["id"],
            referrer_user_id=row["referrer_user_id"],
            invited_user_id=row["invited_user_id"],
            invited_name=row["invited_name"],
            bonus_stars=int(row["bonus_stars"]),
            bonus_ton=round(float(row["bonus_ton"]), 2),
            created_at=row["created_at"],
        )

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _today_iso() -> str:
        return date.today().isoformat()
