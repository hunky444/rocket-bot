from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl

from aiohttp import web

from app.services.container import rocket_service, settings, subscription_service


WEBAPP_DIR = Path(__file__).resolve().parent / "static"


@web.middleware
async def telegram_auth_middleware(request: web.Request, handler):
    if request.path in {"/webapp"} or request.path.startswith("/webapp/static/"):
        return await handler(request)

    auth_context = _resolve_auth_context(request)
    if auth_context is None:
        return web.json_response({"error": "unauthorized"}, status=401)

    request["telegram_user_id"] = auth_context["user_id"]
    request["auth_mode"] = auth_context["mode"]
    return await handler(request)


async def handle_index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(WEBAPP_DIR / "index.html")


async def handle_profile(request: web.Request) -> web.Response:
    telegram_user_id = request["telegram_user_id"]
    user = subscription_service.ensure_user(telegram_user_id)
    stats, history = rocket_service.get_profile_stats(telegram_user_id)
    leaderboard = rocket_service.get_leaderboard(limit=8)
    referral_count = max(stats.rounds_total // 4, 0)
    referral_stars_earned = referral_count * 250 + max(stats.wins_total * 15, 0)
    referral_ton_earned = round(referral_count * 0.15, 2)
    return web.json_response(
        {
            "auth_mode": request["auth_mode"],
            "user": {
                "telegram_user_id": user.telegram_user_id,
                "first_name": user.first_name,
                "username": user.username,
                "plan": user.plan,
                "stars_balance": user.demo_balance_stars,
                "ton_balance": round(user.demo_balance_ton, 2),
                "auto_cashout_xtr": user.auto_cashout_xtr,
                "auto_cashout_ton": user.auto_cashout_ton,
                "referral_code": f"ROCKET{telegram_user_id}",
            },
            "wallet": {
                "deposit_presets_stars": [1000, 2500, 5000],
                "withdraw_presets_stars": [500, 1500, 3000],
                "deposit_presets_ton": [2, 5, 10],
                "withdraw_presets_ton": [1, 3, 5],
            },
            "stats": {
                "rounds_total": stats.rounds_total,
                "wins_total": stats.wins_total,
                "losses_total": stats.losses_total,
                "best_multiplier": stats.best_multiplier,
                "profit_stars": stats.total_profit_stars,
                "profit_ton": stats.total_profit_ton,
                "win_rate": round((stats.wins_total / stats.rounds_total) * 100, 1) if stats.rounds_total else 0,
            },
            "referrals": {
                "invited_total": referral_count,
                "earned_stars": referral_stars_earned,
                "earned_ton": referral_ton_earned,
                "share_text": f"Заходи в Crash Rocket по коду ROCKET{telegram_user_id}",
            },
            "history": [
                {
                    "status": item.status,
                    "currency": item.currency,
                    "bet_amount": item.bet_amount,
                    "exit_multiplier": item.exit_multiplier,
                    "profit_amount": item.profit_amount,
                }
                for item in history[:6]
            ],
            "leaderboard": [
                {
                    "name": entry.first_name or entry.username or f"id {entry.telegram_user_id}",
                    "rounds_total": entry.rounds_total,
                    "wins_total": entry.wins_total,
                    "profit_stars": entry.total_profit_stars,
                    "profit_ton": entry.total_profit_ton,
                    "best_multiplier": entry.best_multiplier,
                }
                for entry in leaderboard
            ],
        }
    )


async def handle_start_round(request: web.Request) -> web.Response:
    payload = await request.json()
    telegram_user_id = request["telegram_user_id"]
    currency = str(payload.get("currency", "XTR")).upper()
    bet_amount = float(payload.get("bet_amount", 0))
    auto_cashout = payload.get("auto_cashout_multiplier")
    auto_cashout_value = float(auto_cashout) if auto_cashout not in {None, ""} else None
    subscription_service.ensure_user(telegram_user_id)

    try:
        round_state = await rocket_service.start_round(
            telegram_user_id=telegram_user_id,
            currency=currency,
            bet_amount=bet_amount,
            auto_cashout_multiplier=auto_cashout_value,
        )
    except ValueError as exc:
        return web.json_response({"error": str(exc)}, status=400)

    stars_balance, ton_balance = rocket_service.get_balances(telegram_user_id)
    return web.json_response({"round": _serialize_round(round_state), "balances": {"stars": stars_balance, "ton": ton_balance}})


async def handle_round_state(request: web.Request) -> web.Response:
    telegram_user_id = request["telegram_user_id"]
    round_state = await rocket_service.tick_round(telegram_user_id)
    stars_balance, ton_balance = rocket_service.get_balances(telegram_user_id)
    return web.json_response({"round": _serialize_round(round_state) if round_state is not None else None, "balances": {"stars": stars_balance, "ton": ton_balance}})


async def handle_cashout(request: web.Request) -> web.Response:
    telegram_user_id = request["telegram_user_id"]
    round_state = await rocket_service.cash_out(telegram_user_id)
    stars_balance, ton_balance = rocket_service.get_balances(telegram_user_id)
    return web.json_response({"round": _serialize_round(round_state) if round_state is not None else None, "balances": {"stars": stars_balance, "ton": ton_balance}})


async def handle_wallet(request: web.Request) -> web.Response:
    payload = await request.json()
    telegram_user_id = request["telegram_user_id"]
    action = payload.get("action", "add")
    currency = str(payload.get("currency", "XTR")).upper()
    amount = float(payload.get("amount", 0))

    if action == "reset":
        stars_balance, ton_balance = rocket_service.reset_balances(telegram_user_id)
    else:
        if action == "withdraw":
            amount = -amount
        stars_balance, ton_balance = rocket_service.adjust_balance(telegram_user_id, currency, amount)

    return web.json_response({"balances": {"stars": stars_balance, "ton": ton_balance}})


async def handle_auto_cashout(request: web.Request) -> web.Response:
    payload = await request.json()
    telegram_user_id = request["telegram_user_id"]
    currency = str(payload.get("currency", "XTR")).upper()
    raw_multiplier = payload.get("multiplier")
    multiplier = float(raw_multiplier) if raw_multiplier not in {None, ""} else None
    saved = rocket_service.set_auto_cashout(telegram_user_id, currency, multiplier)
    return web.json_response({"currency": currency, "multiplier": saved})


def create_webapp() -> web.Application:
    app = web.Application(middlewares=[telegram_auth_middleware])
    app.router.add_get("/webapp", handle_index)
    app.router.add_static("/webapp/static/", WEBAPP_DIR)
    app.router.add_get("/api/profile", handle_profile)
    app.router.add_post("/api/rocket/start", handle_start_round)
    app.router.add_get("/api/rocket/state", handle_round_state)
    app.router.add_post("/api/rocket/cashout", handle_cashout)
    app.router.add_post("/api/wallet", handle_wallet)
    app.router.add_post("/api/preferences/auto-cashout", handle_auto_cashout)
    return app


async def start_webapp_server() -> web.AppRunner:
    app = create_webapp()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.webapp_host, settings.webapp_port)
    await site.start()
    return runner


def _resolve_auth_context(request: web.Request) -> dict[str, Any] | None:
    init_data = request.headers.get("X-Telegram-Init-Data", "").strip()
    if init_data:
        validated = _validate_init_data(init_data)
        if validated is not None:
            return {"user_id": validated["id"], "mode": "telegram"}
        return None

    if settings.webapp_dev_mode:
        query_value = request.query.get("user_id")
        if query_value:
            return {"user_id": int(query_value), "mode": "dev"}
        dev_header = request.headers.get("X-Demo-User-Id", "").strip()
        if dev_header:
            return {"user_id": int(dev_header), "mode": "dev"}

    return None


def _validate_init_data(init_data: str) -> dict[str, Any] | None:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", settings.bot_token.encode("utf-8"), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        return None

    user_payload = pairs.get("user")
    if not user_payload:
        return None
    user_data = json.loads(user_payload)
    if "id" not in user_data:
        return None
    return user_data


def _serialize_round(round_state) -> dict | None:
    if round_state is None:
        return None
    return {
        "currency": round_state.currency,
        "bet_amount": round_state.bet_amount,
        "current_multiplier": round_state.current_multiplier,
        "crash_multiplier": round_state.crash_multiplier,
        "auto_cashout_multiplier": round_state.auto_cashout_multiplier,
        "status": round_state.status,
        "payout_amount": round_state.payout_amount,
    }
