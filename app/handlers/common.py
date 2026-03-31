import asyncio
from contextlib import suppress
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.keyboards.main import (
    alerts_inline_keyboard,
    checkout_inline_keyboard,
    home_inline_keyboard,
    leaderboard_inline_keyboard,
    main_menu_keyboard,
    open_webapp_keyboard,
    paywall_inline_keyboard,
    portfolio_inline_keyboard,
    plans_inline_keyboard,
    profile_inline_keyboard,
    rocket_active_keyboard,
    rocket_finished_keyboard,
    rocket_lobby_keyboard,
)
from app.services.container import (
    alerts_service,
    analytics_service,
    billing_service,
    portfolio_service,
    rocket_service,
    settings,
    subscription_service,
)
from app.services.repository import LeaderboardEntry, RocketHistoryRecord, RocketStatsRecord, UserRecord
from app.services.rocket import RocketRound
from app.services.texts import (
    render_alert_created,
    render_alerts,
    render_budget_response,
    render_checkout,
    render_gift_card_caption,
    render_home,
    render_payment_success,
    render_plans,
    render_portfolio,
    render_portfolio_item_added,
    render_portfolio_teaser,
    render_sell_response,
    render_top_picks,
)

router = Router()
rocket_tasks: dict[int, asyncio.Task[None]] = {}
rocket_currency_preferences: dict[int, str] = {}


@router.message(Command("start"))
async def handle_start(message: Message) -> None:
    user = ensure_user(message)
    market_source, updated_at = analytics_service.get_market_summary()
    await message.answer(
        render_home(user.plan, subscription_service.get_budget_queries_left(user), market_source, updated_at),
        reply_markup=home_inline_keyboard(),
    )
    await message.answer(
        "Быстрые кнопки для игры и профиля ниже.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    await message.answer(
        (
            "Команды:\n"
            "/start - главное меню\n"
            "/help - помощь\n"
            "/plans - тарифы\n"
            "/top - топ идей\n"
            "/budget 5000 - подбор по бюджету\n"
            "/sell - советы по продаже\n"
            "/portfolio - портфель\n"
            "/alerts - алерты\n"
            "/rocket - игра с ракетой\n"
            "/profile - профиль и балансы\n\n"
            "Можно писать и обычным текстом:\n"
            "<code>что купить на 7000</code>\n"
            "<code>ракетка</code>\n"
            "<code>профиль</code>"
        )
    )


@router.message(Command("plans"))
async def handle_plans(message: Message) -> None:
    user = ensure_user(message)
    await message.answer(render_plans(user.plan, billing_service.list_offers()), reply_markup=plans_inline_keyboard())


@router.message(Command("top"))
async def handle_top(message: Message) -> None:
    user = ensure_user(message)
    picks = analytics_service.get_top_picks(limit=3 if user.plan == "free" else 5)
    market_source, updated_at = analytics_service.get_market_summary()
    await message.answer(render_top_picks(picks, user.plan), reply_markup=home_inline_keyboard())
    for pick in picks[:3]:
        await send_gift_card(message, pick, market_source, updated_at)


@router.message(Command("sell"))
async def handle_sell(message: Message) -> None:
    user = ensure_user(message)
    recommendation = analytics_service.get_sell_recommendation()
    await message.answer(render_sell_response(recommendation, user.plan), reply_markup=home_inline_keyboard())


@router.message(Command("portfolio"))
async def handle_portfolio(message: Message) -> None:
    user = ensure_user(message)
    if user.plan == "free":
        await message.answer(render_portfolio_teaser(user.plan), reply_markup=paywall_inline_keyboard())
        return
    summary = portfolio_service.get_summary(user.telegram_user_id)
    await message.answer(render_portfolio(summary, user.plan), reply_markup=portfolio_inline_keyboard())


@router.message(Command("alerts"))
async def handle_alerts(message: Message) -> None:
    user = ensure_user(message)
    existing_alerts = alerts_service.list_user_alerts(user.telegram_user_id)
    await message.answer(render_alerts(existing_alerts, user.plan), reply_markup=alerts_inline_keyboard())


@router.message(Command("rocket"))
async def handle_rocket(message: Message) -> None:
    user = ensure_user(message)
    currency = get_selected_currency(user.telegram_user_id)
    auto_cashout = get_auto_cashout(user.telegram_user_id)
    await message.answer(
        render_rocket_lobby(user, currency, auto_cashout),
        reply_markup=rocket_lobby_keyboard(currency, auto_cashout),
    )
    await message.answer(
        "Можно открыть красивую WebApp-версию с анимацией ракеты.",
        reply_markup=open_webapp_keyboard(settings.webapp_url, user.telegram_user_id),
    )


@router.message(Command("profile"))
async def handle_profile(message: Message) -> None:
    user = ensure_user(message)
    stats, history = rocket_service.get_profile_stats(user.telegram_user_id)
    await message.answer(
        render_profile(user, stats, history),
        reply_markup=profile_inline_keyboard(),
    )


@router.message(Command("leaderboard"))
async def handle_leaderboard(message: Message) -> None:
    ensure_user(message)
    leaderboard = rocket_service.get_leaderboard()
    await message.answer(
        render_leaderboard(leaderboard),
        reply_markup=leaderboard_inline_keyboard(),
    )


@router.message(Command("webapp"))
async def handle_webapp(message: Message) -> None:
    user = ensure_user(message)
    await message.answer(
        "Открыть мини-апку:",
        reply_markup=open_webapp_keyboard(settings.webapp_url, user.telegram_user_id),
    )


@router.message(Command("budget"))
async def handle_budget(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Укажи бюджет так: <code>/budget 5000</code>")
        return

    await process_budget_request(message, command.args)


@router.message(F.text.regexp(r"(?i).*(что купить|what to buy|buy).*(\d+).*"))
async def handle_natural_budget(message: Message) -> None:
    await process_budget_request(message, message.text)


@router.message(F.text.regexp(r"(?i)^(ракетка|ракета|rocket|crash)$"))
async def handle_rocket_text(message: Message) -> None:
    await handle_rocket(message)


@router.message(F.text.regexp(r"(?i)^(профиль|profile|wallet|balance)$"))
async def handle_profile_text(message: Message) -> None:
    await handle_profile(message)


@router.message(F.text.regexp(r"(?i)^(лидерборд|топ игроков|leaderboard|leaders)$"))
async def handle_leaderboard_text(message: Message) -> None:
    await handle_leaderboard(message)


async def process_budget_request(message: Message, raw_budget: str) -> None:
    user = ensure_user(message)

    if not subscription_service.can_use_budget_query(user):
        await message.answer(
            (
                "Лимит бесплатных аналитических запросов на сегодня исчерпан.\n\n"
                "В Pro доступны безлимитные подборки, больше результатов и более свежие данные."
            ),
            reply_markup=paywall_inline_keyboard(),
        )
        return

    budget_request = analytics_service.extract_budget_request(raw_budget)
    if budget_request is None:
        await message.answer("Не смог понять бюджет. Напиши, например: <code>/budget 5000</code>")
        return
    budget, currency = budget_request

    user = subscription_service.register_budget_query(user)
    picks = analytics_service.get_best_buys(budget=budget, plan=user.plan, currency=currency)
    market_source, updated_at = analytics_service.get_market_summary()
    await message.answer(
        render_budget_response(budget, picks, user.plan, market_source, updated_at, currency),
        reply_markup=home_inline_keyboard(),
    )
    for pick in picks[:3]:
        await send_gift_card(message, pick, market_source, updated_at, currency)


@router.message(F.text)
async def handle_fallback(message: Message) -> None:
    text = message.text or ""
    intent = analytics_service.detect_intent(text)
    if intent == "buy":
        await process_budget_request(message, text)
        return
    if intent == "sell":
        await handle_sell(message)
        return
    if intent == "top":
        await handle_top(message)
        return
    if intent == "portfolio":
        await handle_portfolio(message)
        return
    if intent == "alerts":
        await handle_alerts(message)
        return
    lower_text = text.lower()
    if "ракет" in lower_text or "rocket" in lower_text:
        await handle_rocket(message)
        return
    if "проф" in lower_text or "wallet" in lower_text or "balance" in lower_text:
        await handle_profile(message)
        return
    await message.answer(
        "Я не до конца понял запрос.\n\n"
        "Попробуй так:\n"
        "<code>/rocket</code>\n"
        "<code>/profile</code>\n"
        "<code>что купить на 4200 stars</code>\n"
        "<code>что лучше продать сейчас</code>"
    )


@router.callback_query(F.data == "menu:home")
async def callback_home(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    user = ensure_callback_user(callback)
    await callback.message.edit_text(
        render_home(
            user.plan,
            subscription_service.get_budget_queries_left(user),
            *analytics_service.get_market_summary(),
        ),
        reply_markup=home_inline_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:plans")
async def callback_plans(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    user = ensure_callback_user(callback)
    await callback.message.edit_text(
        render_plans(user.plan, billing_service.list_offers()),
        reply_markup=plans_inline_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:help")
async def callback_help(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await callback.message.edit_text(
        "Что можно спросить:\n\n"
        "что купить на 5000 stars\n"
        "что купить на 70 тон\n"
        "что лучше продать сейчас\n"
        "покажи топ подарков\n"
        "покажи профиль\n"
        "/rocket\n"
        "/profile",
        reply_markup=home_inline_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:top")
async def callback_top(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    user = ensure_callback_user(callback)
    picks = analytics_service.get_top_picks(limit=3 if user.plan == "free" else 5)
    market_source, updated_at = analytics_service.get_market_summary()
    await callback.message.edit_text(render_top_picks(picks, user.plan), reply_markup=home_inline_keyboard())
    for pick in picks[:3]:
        await send_gift_card(callback.message, pick, market_source, updated_at)
    await callback.answer()


@router.callback_query(F.data == "menu:sell")
async def callback_sell(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    user = ensure_callback_user(callback)
    recommendation = analytics_service.get_sell_recommendation()
    await callback.message.edit_text(render_sell_response(recommendation, user.plan), reply_markup=home_inline_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:portfolio")
async def callback_portfolio(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    user = ensure_callback_user(callback)
    if user.plan == "free":
        await callback.message.edit_text(render_portfolio_teaser(user.plan), reply_markup=paywall_inline_keyboard())
    else:
        summary = portfolio_service.get_summary(user.telegram_user_id)
        await callback.message.edit_text(render_portfolio(summary, user.plan), reply_markup=portfolio_inline_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:alerts")
async def callback_alerts(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    user = ensure_callback_user(callback)
    existing_alerts = alerts_service.list_user_alerts(user.telegram_user_id)
    await callback.message.edit_text(render_alerts(existing_alerts, user.plan), reply_markup=alerts_inline_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:profile")
async def callback_profile_menu(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    user = ensure_callback_user(callback)
    stats, history = rocket_service.get_profile_stats(user.telegram_user_id)
    await callback.message.edit_text(
        render_profile(user, stats, history),
        reply_markup=profile_inline_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:leaderboard")
async def callback_leaderboard_menu(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    ensure_callback_user(callback)
    leaderboard = rocket_service.get_leaderboard()
    await callback.message.edit_text(
        render_leaderboard(leaderboard),
        reply_markup=leaderboard_inline_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:rocket")
async def callback_rocket_menu(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    user = ensure_callback_user(callback)
    currency = get_selected_currency(user.telegram_user_id)
    auto_cashout = get_auto_cashout(user.telegram_user_id)
    await callback.message.edit_text(
        render_rocket_lobby(user, currency, auto_cashout),
        reply_markup=rocket_lobby_keyboard(currency, auto_cashout),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rocket:currency:"))
async def callback_rocket_currency(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    user = ensure_callback_user(callback)
    currency = callback.data.split(":")[-1].upper()
    rocket_currency_preferences[user.telegram_user_id] = currency
    auto_cashout = get_auto_cashout(user.telegram_user_id)
    await callback.message.edit_text(
        render_rocket_lobby(user, currency, auto_cashout),
        reply_markup=rocket_lobby_keyboard(currency, auto_cashout),
    )
    await callback.answer(f"Выбрана валюта {currency}")


@router.callback_query(F.data.startswith("rocket:auto:"))
async def callback_rocket_auto(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    user = ensure_callback_user(callback)
    raw_value = callback.data.split(":")[-1]
    currency = get_selected_currency(user.telegram_user_id)
    auto_cashout = rocket_service.set_auto_cashout(
        user.telegram_user_id,
        currency,
        None if raw_value == "off" else float(raw_value),
    )
    await callback.message.edit_text(
        render_rocket_lobby(user, currency, auto_cashout),
        reply_markup=rocket_lobby_keyboard(currency, auto_cashout),
    )
    await callback.answer("Автокэшаут обновлен")


@router.callback_query(F.data.startswith("rocket:bet:"))
async def callback_rocket_bet(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return

    ensure_callback_user(callback)
    _, _, currency, raw_bet = callback.data.split(":")
    bet_amount = float(raw_bet)

    try:
        round_state = await rocket_service.start_round(
            callback.from_user.id,
            currency,
            bet_amount,
            get_auto_cashout(callback.from_user.id),
        )
    except ValueError as exc:
        reason = str(exc)
        if reason == "active_round":
            await callback.answer("Сначала заверши текущий раунд", show_alert=True)
            return
        if reason == "insufficient_balance":
            await callback.answer("Недостаточно баланса для этой ставки", show_alert=True)
            return
        if reason == "bet_too_small":
            minimum_text = "100 Stars" if currency == "XTR" else "0.5 TON"
            await callback.answer(f"Минимальная ставка {minimum_text}", show_alert=True)
            return
        await callback.answer("Не удалось начать раунд", show_alert=True)
        return

    await callback.message.edit_text(
        render_rocket_flight(round_state, *rocket_service.get_balances(callback.from_user.id)),
        reply_markup=rocket_active_keyboard(),
    )
    await replace_rocket_task(
        callback.from_user.id,
        asyncio.create_task(run_rocket_round(callback.message, callback.from_user.id)),
    )
    await callback.answer("Ставка принята")


@router.callback_query(F.data == "rocket:cashout")
async def callback_rocket_cashout(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return

    round_state = await rocket_service.cash_out(callback.from_user.id)
    await cancel_rocket_task(callback.from_user.id)
    if round_state is None:
        await callback.answer("Раунд уже завершен", show_alert=True)
        return

    stars_balance, ton_balance = rocket_service.get_balances(callback.from_user.id)
    if round_state.status == "crashed":
        await callback.message.edit_text(
            render_rocket_crashed(round_state, stars_balance, ton_balance),
            reply_markup=rocket_finished_keyboard(),
        )
        await callback.answer("Ракета уже взорвалась")
        return

    await callback.message.edit_text(
        render_rocket_cashed_out(round_state, stars_balance, ton_balance),
        reply_markup=rocket_finished_keyboard(),
    )
    await callback.answer("Выигрыш зачислен")


@router.callback_query(F.data.startswith("wallet:add:"))
async def callback_wallet_add(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    ensure_callback_user(callback)
    _, _, currency, raw_amount = callback.data.split(":")
    stars_balance, ton_balance = rocket_service.adjust_balance(callback.from_user.id, currency, float(raw_amount))
    refreshed_user = subscription_service.ensure_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
    stats, history = rocket_service.get_profile_stats(callback.from_user.id)
    await callback.message.edit_text(
        render_profile(refreshed_user, stats, history, notice=f"Демо-пополнение: +{format_money(float(raw_amount), currency)}"),
        reply_markup=profile_inline_keyboard(),
    )
    await callback.answer(f"Баланс обновлен: {stars_balance} Stars / {ton_balance:.2f} TON")


@router.callback_query(F.data.startswith("wallet:withdraw:"))
async def callback_wallet_withdraw(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    ensure_callback_user(callback)
    _, _, currency, raw_amount = callback.data.split(":")
    amount = float(raw_amount)
    stars_balance, ton_balance = rocket_service.get_balances(callback.from_user.id)
    if (currency == "XTR" and amount > stars_balance) or (currency == "TON" and amount > ton_balance):
        await callback.answer("Недостаточно средств для вывода", show_alert=True)
        return

    rocket_service.adjust_balance(callback.from_user.id, currency, -amount)
    refreshed_user = subscription_service.ensure_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
    stats, history = rocket_service.get_profile_stats(callback.from_user.id)
    await callback.message.edit_text(
        render_profile(refreshed_user, stats, history, notice=f"Демо-вывод: -{format_money(amount, currency)}"),
        reply_markup=profile_inline_keyboard(),
    )
    await callback.answer("Вывод выполнен")


@router.callback_query(F.data == "wallet:reset")
async def callback_wallet_reset(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    ensure_callback_user(callback)
    active_round = await rocket_service.get_active_round(callback.from_user.id)
    if active_round is not None:
        await callback.answer("Нельзя сбросить балансы во время полета", show_alert=True)
        return

    rocket_service.reset_balances(callback.from_user.id)
    refreshed_user = subscription_service.ensure_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
    stats, history = rocket_service.get_profile_stats(callback.from_user.id)
    await callback.message.edit_text(
        render_profile(refreshed_user, stats, history, notice="Демо-балансы сброшены к стартовым значениям."),
        reply_markup=profile_inline_keyboard(),
    )
    await callback.answer("Балансы сброшены")


@router.callback_query(F.data.startswith("budget:"))
async def callback_budget(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    budget_value = callback.data.split(":", maxsplit=1)[1]
    user = ensure_callback_user(callback)

    if not subscription_service.can_use_budget_query(user):
        await callback.message.edit_text(
            "Лимит Free исчерпан. Открой тарифы, чтобы проверить Pro/Premium flow.",
            reply_markup=paywall_inline_keyboard(),
        )
        await callback.answer()
        return

    budget_request = analytics_service.extract_budget_request(budget_value)
    if budget_request is None:
        await callback.answer("Не смог распознать бюджет", show_alert=True)
        return
    budget, currency = budget_request

    user = subscription_service.register_budget_query(user)
    picks = analytics_service.get_best_buys(budget=budget, plan=user.plan, currency=currency)
    market_source, updated_at = analytics_service.get_market_summary()
    await callback.message.edit_text(
        render_budget_response(budget, picks, user.plan, market_source, updated_at, currency),
        reply_markup=home_inline_keyboard(),
    )
    for pick in picks[:3]:
        await send_gift_card(callback.message, pick, market_source, updated_at, currency)
    await callback.answer()


@router.callback_query(F.data.startswith("checkout:"))
async def callback_checkout(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    selected_plan = callback.data.split(":", maxsplit=1)[1]
    offer = billing_service.get_offer(selected_plan)
    if offer is None:
        await callback.answer("Неизвестный план", show_alert=True)
        return

    payment = billing_service.create_demo_checkout(callback.from_user.id, selected_plan)
    await callback.message.edit_text(
        render_checkout(offer, payment.checkout_url),
        reply_markup=checkout_inline_keyboard(selected_plan),
    )
    await callback.answer("Checkout создан")


@router.callback_query(F.data.startswith("confirm_checkout:"))
async def callback_confirm_checkout(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    selected_plan = callback.data.split(":", maxsplit=1)[1]
    subscription = billing_service.confirm_demo_checkout(callback.from_user.id, selected_plan)
    await callback.message.edit_text(
        render_payment_success(subscription.plan),
        reply_markup=home_inline_keyboard(),
    )
    await callback.answer("Оплата подтверждена")


@router.callback_query(F.data.startswith("portfolio_add:"))
async def callback_portfolio_add(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    user = ensure_callback_user(callback)
    if user.plan == "free":
        await callback.message.edit_text(render_portfolio_teaser(user.plan), reply_markup=paywall_inline_keyboard())
        await callback.answer()
        return
    gift_slug = callback.data.split(":", maxsplit=1)[1]
    position = portfolio_service.add_demo_item(user.telegram_user_id, gift_slug)
    if position is None:
        await callback.answer("Не удалось добавить позицию", show_alert=True)
        return
    summary = portfolio_service.get_summary(user.telegram_user_id)
    await callback.message.edit_text(
        render_portfolio_item_added(position.title, position.buy_price_stars) + "\n\n" + render_portfolio(summary, user.plan),
        reply_markup=portfolio_inline_keyboard(),
    )
    await callback.answer("Позиция добавлена")


@router.callback_query(F.data.startswith("alert_budget:"))
async def callback_alert_budget(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    user = ensure_callback_user(callback)
    budget = int(callback.data.split(":", maxsplit=1)[1])
    alert = alerts_service.create_budget_alert(user.telegram_user_id, budget)
    alerts = alerts_service.list_user_alerts(user.telegram_user_id)
    await callback.message.edit_text(
        render_alert_created(alert.description) + "\n\n" + render_alerts(alerts, user.plan),
        reply_markup=alerts_inline_keyboard(),
    )
    await callback.answer("Alert создан")


async def run_rocket_round(message: Message, telegram_user_id: int) -> None:
    try:
        while True:
            await asyncio.sleep(0.9)
            round_state = await rocket_service.tick_round(telegram_user_id)
            if round_state is None:
                return

            stars_balance, ton_balance = rocket_service.get_balances(telegram_user_id)
            if round_state.status == "crashed":
                with suppress(Exception):
                    await message.edit_text(
                        render_rocket_crashed(round_state, stars_balance, ton_balance),
                        reply_markup=rocket_finished_keyboard(),
                    )
                return
            if round_state.status == "cashed_out":
                with suppress(Exception):
                    await message.edit_text(
                        render_rocket_cashed_out(round_state, stars_balance, ton_balance, auto_mode=True),
                        reply_markup=rocket_finished_keyboard(),
                    )
                return

            with suppress(Exception):
                await message.edit_text(
                    render_rocket_flight(round_state, stars_balance, ton_balance),
                    reply_markup=rocket_active_keyboard(),
                )
    finally:
        rocket_tasks.pop(telegram_user_id, None)


async def replace_rocket_task(telegram_user_id: int, task: asyncio.Task[None]) -> None:
    previous_task = rocket_tasks.get(telegram_user_id)
    if previous_task is not None and not previous_task.done():
        previous_task.cancel()
        with suppress(asyncio.CancelledError):
            await previous_task
    rocket_tasks[telegram_user_id] = task


async def cancel_rocket_task(telegram_user_id: int) -> None:
    task = rocket_tasks.pop(telegram_user_id, None)
    if task is None or task.done():
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


def ensure_user(message: Message) -> UserRecord:
    return subscription_service.ensure_user(message.from_user.id, message.from_user.username, message.from_user.first_name)


def ensure_callback_user(callback: CallbackQuery) -> UserRecord:
    return subscription_service.ensure_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)


def get_selected_currency(telegram_user_id: int) -> str:
    return rocket_currency_preferences.get(telegram_user_id, "XTR")


def get_auto_cashout(telegram_user_id: int) -> float | None:
    return rocket_service.get_auto_cashout(telegram_user_id, get_selected_currency(telegram_user_id))


def render_rocket_lobby(user: UserRecord, currency: str, auto_cashout: float | None) -> str:
    currency_name = "Stars" if currency == "XTR" else "TON"
    minimum_text = "100 Stars" if currency == "XTR" else "0.5 TON"
    auto_text = "OFF" if auto_cashout is None else f"{auto_cashout:.2f}x"
    return (
        "Ракетка\n\n"
        "Ставишь сумму, ракета летит, коэффициент растет. Если успеешь нажать "
        "<b>Забрать выигрыш</b> до взрыва, ставка умножится на текущий коэффициент.\n\n"
        f"Баланс Stars: <b>{user.demo_balance_stars}</b>\n"
        f"Баланс TON: <b>{user.demo_balance_ton:.2f}</b>\n"
        f"Текущая валюта игры: <b>{currency_name}</b>\n"
        f"Автокэшаут: <b>{auto_text}</b>\n"
        f"Минимальная ставка: <b>{minimum_text}</b>\n\n"
        "Выбери валюту и размер ставки."
    )


def render_rocket_flight(round_state: RocketRound, stars_balance: int, ton_balance: float) -> str:
    potential_win = format_money(round_state.bet_amount * round_state.current_multiplier, round_state.currency)
    auto_text = "ручной" if round_state.auto_cashout_multiplier is None else f"auto {round_state.auto_cashout_multiplier:.2f}x"
    return (
        "Ракета в полете\n\n"
        f"Ставка: <b>{format_money(round_state.bet_amount, round_state.currency)}</b>\n"
        f"Текущий коэффициент: <b>{round_state.current_multiplier:.2f}x</b>\n"
        f"Режим: <b>{auto_text}</b>\n"
        f"Потенциальный выигрыш: <b>{potential_win}</b>\n"
        f"Баланс Stars: <b>{stars_balance}</b>\n"
        f"Баланс TON: <b>{ton_balance:.2f}</b>\n\n"
        f"{render_rocket_track(round_state.current_multiplier)}\n"
        "Жми кнопку ниже до взрыва."
    )


def render_rocket_cashed_out(round_state: RocketRound, stars_balance: int, ton_balance: float, auto_mode: bool = False) -> str:
    profit = round_state.payout_amount - round_state.bet_amount
    title = "Автокэшаут сработал" if auto_mode else "Ты успел забрать"
    return (
        f"{title}\n\n"
        f"Коэффициент: <b>{round_state.current_multiplier:.2f}x</b>\n"
        f"Ставка: <b>{format_money(round_state.bet_amount, round_state.currency)}</b>\n"
        f"Выплата: <b>{format_money(round_state.payout_amount, round_state.currency)}</b>\n"
        f"Чистая прибыль: <b>{format_signed_money(profit, round_state.currency)}</b>\n"
        f"Баланс Stars: <b>{stars_balance}</b>\n"
        f"Баланс TON: <b>{ton_balance:.2f}</b>"
    )


def render_rocket_crashed(round_state: RocketRound, stars_balance: int, ton_balance: float) -> str:
    return (
        "Ракета взорвалась\n\n"
        f"Краш на: <b>{round_state.current_multiplier:.2f}x</b>\n"
        f"Ставка сгорела: <b>{format_money(round_state.bet_amount, round_state.currency)}</b>\n"
        f"Баланс Stars: <b>{stars_balance}</b>\n"
        f"Баланс TON: <b>{ton_balance:.2f}</b>\n\n"
        "Запускай новый раунд."
    )


def render_profile(
    user: UserRecord,
    stats: RocketStatsRecord,
    history: list[RocketHistoryRecord],
    notice: str | None = None,
) -> str:
    history_lines = []
    for item in history[:5]:
        exit_label = f"{item.exit_multiplier:.2f}x" if item.exit_multiplier is not None else "boom"
        history_lines.append(
            f"- {item.status} | {format_money(item.bet_amount, item.currency)} | выход {exit_label} | {format_signed_money(item.profit_amount, item.currency)}"
        )
    history_block = "\n".join(history_lines) if history_lines else "- пока нет раундов"
    notice_block = f"{notice}\n\n" if notice else ""
    return (
        "Профиль игрока\n\n"
        f"{notice_block}"
        f"План: <b>{user.plan.upper()}</b>\n"
        f"Баланс Stars: <b>{user.demo_balance_stars}</b>\n"
        f"Баланс TON: <b>{user.demo_balance_ton:.2f}</b>\n\n"
        "Статистика ракеты\n"
        f"Раундов: <b>{stats.rounds_total}</b>\n"
        f"Побед: <b>{stats.wins_total}</b>\n"
        f"Поражений: <b>{stats.losses_total}</b>\n"
        f"Лучший множитель: <b>{stats.best_multiplier:.2f}x</b>\n"
        f"Оборот Stars: <b>{stats.total_wagered_stars}</b>\n"
        f"Прибыль Stars: <b>{stats.total_profit_stars:+}</b>\n"
        f"Оборот TON: <b>{stats.total_wagered_ton:.2f}</b>\n"
        f"Прибыль TON: <b>{stats.total_profit_ton:+.2f}</b>\n\n"
        "Последние раунды\n"
        f"{history_block}\n\n"
        "Кнопками ниже можно делать demo-пополнение и demo-вывод, как в классических ракетках."
    )


def render_leaderboard(entries: list[LeaderboardEntry]) -> str:
    if not entries:
        return "Лидерборд пока пуст. Сыграй первый раунд."
    lines = ["Лидерборд Crash\n"]
    for index, entry in enumerate(entries, start=1):
        name = entry.first_name or entry.username or f"id {entry.telegram_user_id}"
        lines.append(
            f"{index}. <b>{name}</b> | раунды {entry.rounds_total} | wins {entry.wins_total} | {entry.total_profit_stars:+} Stars | {entry.total_profit_ton:+.2f} TON | best {entry.best_multiplier:.2f}x"
        )
    return "\n".join(lines)


def render_rocket_track(multiplier: float) -> str:
    stages = min(max(int((multiplier - 1) * 2.4), 0), 12)
    return "·" * stages + "🚀" + "·" * (12 - stages)


def format_money(amount: float, currency: str) -> str:
    if currency == "XTR":
        return f"{int(round(amount))} Stars"
    return f"{amount:.2f} TON"


def format_signed_money(amount: float, currency: str) -> str:
    if currency == "XTR":
        return f"{int(round(amount)):+} Stars"
    return f"{amount:+.2f} TON"


async def send_gift_card(message: Message, pick, market_source: str, updated_at: str, currency: str = "XTR") -> None:
    caption = render_gift_card_caption(pick, market_source, updated_at, currency)
    image_path = getattr(pick, "image_path", "")
    if image_path:
        local_file = Path(image_path)
        if local_file.exists():
            if local_file.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                with suppress(Exception):
                    await message.answer_photo(photo=FSInputFile(str(local_file)), caption=caption)
                    return
            with suppress(Exception):
                await message.answer_document(document=FSInputFile(str(local_file)), caption=caption)
                return
    with suppress(Exception):
        if pick.image_url:
            await message.answer_photo(photo=pick.image_url, caption=caption)
            return
    with suppress(Exception):
        if pick.image_url:
            await message.answer_document(document=pick.image_url, caption=caption)
            return
    await message.answer(caption)
