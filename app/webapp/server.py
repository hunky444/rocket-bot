from __future__ import annotations

import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote

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
    wallet_history = rocket_service.get_wallet_transactions(telegram_user_id)
    referrals = rocket_service.get_referrals(telegram_user_id)

    referral_code = f"ROCKET{telegram_user_id}"
    share_text = f"Играй в Crash Rocket и используй мой код {referral_code}"
    share_link = f"https://t.me/share/url?text={quote(share_text)}"
    win_rate = round((stats.wins_total / stats.rounds_total) * 100, 1) if stats.rounds_total else 0.0
    average_profit_stars = round(stats.total_profit_stars / stats.rounds_total) if stats.rounds_total else 0
    average_profit_ton = round(stats.total_profit_ton / stats.rounds_total, 2) if stats.rounds_total else 0.0

    deposit_total_stars = sum(tx.amount for tx in wallet_history if tx.currency == "XTR" and tx.action == "deposit")
    withdraw_total_stars = abs(sum(tx.amount for tx in wallet_history if tx.currency == "XTR" and tx.action == "withdraw"))
    deposit_total_ton = round(sum(tx.amount for tx in wallet_history if tx.currency == "TON" and tx.action == "deposit"), 2)
    withdraw_total_ton = round(abs(sum(tx.amount for tx in wallet_history if tx.currency == "TON" and tx.action == "withdraw")), 2)
    earned_stars = sum(item.bonus_stars for item in referrals)
    earned_ton = round(sum(item.bonus_ton for item in referrals), 2)

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
                "referral_code": referral_code,
            },
            "wallet": {
                "deposit_presets_stars": [250, 500, 1000, 2500],
                "withdraw_presets_stars": [250, 500, 1000],
                "deposit_presets_ton": [0.5, 1.0, 2.5, 5.0],
                "withdraw_presets_ton": [0.5, 1.0, 2.0],
                "summary": {
                    "deposit_total_stars": int(round(deposit_total_stars)),
                    "withdraw_total_stars": int(round(withdraw_total_stars)),
                    "deposit_total_ton": deposit_total_ton,
                    "withdraw_total_ton": withdraw_total_ton,
                },
                "transactions": [
                    {
                        "action": item.action,
                        "currency": item.currency,
                        "amount": item.amount,
                        "balance_after": item.balance_after,
                        "note": item.note,
                        "created_at": item.created_at,
                    }
                    for item in wallet_history[:10]
                ],
            },
            "stats": {
                "rounds_total": stats.rounds_total,
                "wins_total": stats.wins_total,
                "losses_total": stats.losses_total,
                "best_multiplier": stats.best_multiplier,
                "profit_stars": stats.total_profit_stars,
                "profit_ton": stats.total_profit_ton,
                "wagered_stars": stats.total_wagered_stars,
                "wagered_ton": stats.total_wagered_ton,
                "payout_stars": stats.total_payout_stars,
                "payout_ton": stats.total_payout_ton,
                "win_rate": win_rate,
                "average_profit_stars": average_profit_stars,
                "average_profit_ton": average_profit_ton,
            },
            "referrals": {
                "invited_total": len(referrals),
                "earned_stars": earned_stars,
                "earned_ton": earned_ton,
                "share_link": share_link,
                "share_text": share_text,
                "invited": [
                    {
                        "invited_user_id": item.invited_user_id,
                        "invited_name": item.invited_name,
                        "bonus_stars": item.bonus_stars,
                        "bonus_ton": item.bonus_ton,
                        "created_at": item.created_at,
                    }
                    for item in referrals
                ],
            },
            "history": [
                {
                    "status": item.status,
                    "slot_index": item.slot_index,
                    "currency": item.currency,
                    "bet_amount": item.bet_amount,
                    "exit_multiplier": item.exit_multiplier,
                    "profit_amount": item.profit_amount,
                    "created_at": item.created_at,
                }
                for item in history[:10]
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
    slots = payload.get("slots")
    subscription_service.ensure_user(telegram_user_id)

    try:
        round_state = await rocket_service.start_round(
            telegram_user_id=telegram_user_id,
            currency=currency,
            bet_amount=bet_amount,
            auto_cashout_multiplier=auto_cashout_value,
            slots=slots,
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
    payload = await request.json()
    telegram_user_id = request["telegram_user_id"]
    slot_index = payload.get("slot_index")
    try:
        round_state = await rocket_service.cash_out(
            telegram_user_id,
            int(slot_index) if slot_index not in {None, ""} else None,
        )
    except ValueError as exc:
        return web.json_response({"error": str(exc)}, status=400)
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
        effective_action = "withdraw" if action == "withdraw" else "deposit"
        signed_amount = -amount if action == "withdraw" else amount
        stars_balance, ton_balance = rocket_service.adjust_balance(
            telegram_user_id,
            currency,
            signed_amount,
            action=effective_action,
        )

    return web.json_response({"balances": {"stars": stars_balance, "ton": ton_balance}})


async def handle_auto_cashout(request: web.Request) -> web.Response:
    payload = await request.json()
    telegram_user_id = request["telegram_user_id"]
    currency = str(payload.get("currency", "XTR")).upper()
    raw_multiplier = payload.get("multiplier")
    multiplier = float(raw_multiplier) if raw_multiplier not in {None, ""} else None
    saved = rocket_service.set_auto_cashout(telegram_user_id, currency, multiplier)
    return web.json_response({"currency": currency, "multiplier": saved})


async def handle_activate_referral(request: web.Request) -> web.Response:
    payload = await request.json()
    telegram_user_id = request["telegram_user_id"]
    referral_code = str(payload.get("referral_code", "")).strip()
    try:
        entry = rocket_service.activate_referral_code(telegram_user_id, referral_code)
    except ValueError as exc:
        return web.json_response({"error": str(exc)}, status=400)
    if entry is None:
        return web.json_response({"error": "referral_not_applied"}, status=400)
    return web.json_response(
        {
            "ok": True,
            "referral": {
                "invited_user_id": entry.invited_user_id,
                "bonus_stars": entry.bonus_stars,
                "bonus_ton": entry.bonus_ton,
            },
        }
    )


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
    app.router.add_post("/api/referrals/activate", handle_activate_referral)
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
        "current_multiplier": round_state.current_multiplier,
        "crash_multiplier": round_state.crash_multiplier,
        "status": round_state.status,
        "elapsed_seconds": round(max(time.monotonic() - round_state.created_monotonic, 0), 3),
        "slots": [
            {
                "slot_index": slot.slot_index,
                "bet_amount": slot.bet_amount,
                "current_multiplier": slot.current_multiplier,
                "auto_cashout_multiplier": slot.auto_cashout_multiplier,
                "status": slot.status,
                "payout_amount": slot.payout_amount,
            }
            for slot in round_state.slots
        ],
    }
