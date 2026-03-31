from __future__ import annotations

from app.services.alerts import UserAlert
from app.services.analytics import GiftPick, SellRecommendation
from app.services.billing import PlanOffer
from app.services.portfolio import PortfolioSummary


def render_home(plan: str, queries_left: int | None, market_source: str, updated_at: str) -> str:
    limit_line = (
        "Запросов по бюджету сегодня: без лимита"
        if queries_left is None
        else f"Бесплатных запросов по бюджету осталось сегодня: {queries_left}"
    )
    return (
        "Gift Analyst Bot\n\n"
        "Я могу помочь:\n"
        "- подбирать подарки под бюджет\n"
        "- находить интересные идеи по рынку\n"
        "- подсказывать по продаже\n"
        "- вести портфель и алерты\n\n"
        f"Твой план: <b>{plan.upper()}</b>\n"
        f"{limit_line}\n\n"
        f"Источник данных: <code>{market_source}</code>\n"
        f"Последнее обновление рынка: <code>{updated_at}</code>\n\n"
        "Напиши запрос обычным текстом, например:\n"
        "<code>что купить на 5000 stars</code>\n"
        "<code>что лучше продать сейчас</code>"
    )


def render_plans(current_plan: str, offers: list[PlanOffer]) -> str:
    offers_block = []
    for offer in offers:
        features = "\n".join(f"- {feature}" for feature in offer.features)
        offers_block.append(
            f"<b>{offer.title}</b> — {offer.price_stars} Stars / месяц\n{features}"
        )
    return (
        f"Текущий план: <b>{current_plan.upper()}</b>\n\n"
        "Free\n"
        "- до 5 budget-запросов в день\n"
        "- 2 результата в подборке\n"
        "- базовые sell hints\n\n"
        + "\n\n".join(offers_block)
        + "\n\nОплата тарифа открывает больше результатов, расширенную аналитику и дополнительные функции."
    )


def render_paywall(feature_name: str) -> str:
    return (
        f"Функция <b>{feature_name}</b> доступна только в Pro и Premium.\n\n"
        "В платных планах можно открыть:\n"
        "- больше аналитических подборок\n"
        "- портфель и watchlist\n"
        "- sell advice глубже\n"
        "- быстрые сигналы и расширенные фильтры\n\n"
        "Открой тарифы, чтобы получить доступ к этой функции."
    )


def render_budget_response(budget: int, picks: list[GiftPick], plan: str, market_source: str, updated_at: str, currency: str) -> str:
    if not picks:
        if currency == "TON":
            return (
                f"На бюджет до <b>{budget} TON</b> сейчас не нашел надежных вариантов.\n\n"
                "Сейчас живой источник подключен для подарков в Stars. "
                "Для корректной TON-аналитики нужно отдельно подключить resale/collectible market."
            )
        return (
            f"На бюджет до <b>{budget} {currency}</b> подходящих вариантов сейчас не нашел.\n\n"
            "Попробуй увеличить бюджет или изменить критерии запроса."
        )

    lines = [
        f"Подборка до <b>{budget} {currency}</b>\n",
        "Короткий вывод: я отобрал варианты с дисконтом к медиане и приемлемым риском.\n",
    ]
    for index, pick in enumerate(picks, start=1):
        price_line = f"{pick.price_stars} Stars" if currency == "XTR" else f"{pick.price_ton:.1f} TON"
        median_line = f"{pick.median_stars} Stars" if currency == "XTR" else f"{pick.median_ton:.1f} TON"
        lines.append(
            (
                f"{index}. <b>{pick.title}</b>\n"
                f"Цена: {price_line}\n"
                f"Медиана: {median_line}\n"
                f"Дисконт: {pick.discount_pct}%\n"
                f"Ликвидность: {pick.liquidity}\n"
                f"Риск: {pick.risk}\n"
                f"Почему интересно: {pick.comment}\n"
            )
        )

    if plan == "free":
        lines.append(
            "В Free показывается только часть результатов. В Pro можно открыть больше вариантов, сигналы и расширенный анализ."
        )
    else:
        lines.append(f"Источник: {market_source}. Обновление: {updated_at}.")

    return "\n".join(lines)


def render_top_picks(picks: list[GiftPick], plan: str) -> str:
    lines = ["Топ идей сейчас\n", "Короткий вывод: выше всего ранжируются подарки с лучшим дисконтом к медиане.\n"]
    for index, pick in enumerate(picks, start=1):
        lines.append(
            f"{index}. <b>{pick.title}</b> — {pick.price_stars} Stars, дисконт {pick.discount_pct}%, риск {pick.risk}"
        )

    if plan == "free":
        lines.append("\nВ Pro этот блок можно расширить до полного рейтинга по категориям и стратегиям.")

    return "\n".join(lines)


def render_sell_response(recommendation: SellRecommendation, plan: str) -> str:
    lines = [
        f"Анализ продажи для <b>{recommendation.title}</b>\n",
        f"Быстрая продажа: {recommendation.quick_sell_stars} Stars",
        f"По рынку: {recommendation.market_sell_stars} Stars",
        f"Агрессивная цена: {recommendation.aggressive_sell_stars} Stars",
        f"Комментарий: {recommendation.suggestion}",
    ]

    if plan == "free":
        lines.append("В Pro сюда можно добавить confidence score, ликвидность и историю 24ч / 7д.")

    return "\n".join(lines)


def render_portfolio_teaser(plan: str) -> str:
    if plan == "free":
        return render_paywall("Портфель")
    return (
        "Портфель MVP\n\n"
        "Позже здесь будут:\n"
        "- список подарков пользователя\n"
        "- общая стоимость\n"
        "- точки выхода\n"
        "- алерты по снижению и росту\n\n"
        "Для текущего MVP экран уже открыт по тарифу, но реальные данные портфеля еще не подключены."
    )


def render_portfolio(summary: PortfolioSummary, plan: str) -> str:
    if not summary.positions:
        return (
            "Портфель пока пуст.\n\n"
            "Добавь демо-позицию кнопками ниже, и бот посчитает текущую стоимость и PnL."
        )

    lines = [
        "Портфель\n",
        f"Всего позиций: {len(summary.positions)}",
        f"Сумма входа: {summary.total_cost_stars} Stars",
        f"Текущий floor value: {summary.total_floor_value_stars} Stars",
        f"PnL: {summary.total_pnl_stars:+} Stars\n",
    ]
    for idx, position in enumerate(summary.positions[:5], start=1):
        lines.append(
            f"{idx}. <b>{position.title}</b> — вход {position.buy_price_stars}, сейчас {position.current_price_stars}, PnL {position.pnl_stars:+}"
        )
    if plan == "premium":
        lines.append("\nВ будущем Premium-режим покажет точки выхода и алерты по коллекциям.")
    return "\n".join(lines)


def render_alerts(alerts: list[UserAlert], plan: str) -> str:
    if not alerts:
        return (
            "Алертов пока нет.\n\n"
            "Создай базовый alert на бюджет кнопкой ниже, и бот будет хранить его как персональное условие."
        )
    lines = ["Твои алерты:\n"]
    for alert in alerts[:10]:
        lines.append(f"#{alert.id} — {alert.description} [{alert.status}]")
    if plan == "free":
        lines.append("\nВ Pro позже можно будет добавить больше типов алертов и мгновенные сигналы.")
    return "\n".join(lines)


def render_portfolio_item_added(title: str, buy_price_stars: int) -> str:
    return (
        f"Позиция добавлена в портфель: <b>{title}</b>\n"
        f"Демо-цена входа: {buy_price_stars} Stars"
    )


def render_alert_created(description: str) -> str:
    return (
        "Alert создан.\n\n"
        f"{description}"
    )


def render_gift_card_caption(pick: GiftPick, market_source: str, updated_at: str, currency: str = "XTR") -> str:
    price_line = f"{pick.price_stars} Stars" if currency == "XTR" else f"{pick.price_ton:.1f} TON"
    median_line = f"{pick.median_stars} Stars" if currency == "XTR" else f"{pick.median_ton:.1f} TON"
    model_line = pick.model if pick.model else pick.title
    backdrop_line = pick.backdrop if pick.backdrop else "Не указан"
    return (
        f"<b>{pick.title}</b>\n"
        f"Модель: {model_line}\n"
        f"Фон: {backdrop_line}\n"
        f"Цена: {price_line}\n"
        f"Медиана: {median_line}\n"
        f"Дисконт: {pick.discount_pct}%\n"
        f"Ликвидность: {pick.liquidity}\n"
        f"Риск: {pick.risk}\n"
        f"Комментарий: {pick.comment}\n\n"
        f"Источник: {market_source}\n"
        f"Обновление: {updated_at}"
    )


def render_plan_switched(plan: str) -> str:
    return (
        f"Demo-plan переключен на <b>{plan.upper()}</b>.\n\n"
        "Теперь можно проверить, как меняется выдача, лимиты и доступ к premium-экранам."
    )


def render_checkout(offer: PlanOffer, checkout_url: str | None) -> str:
    checkout_hint = checkout_url or "demo checkout"
    return (
        f"Оформление <b>{offer.title}</b>\n\n"
        f"Цена: {offer.price_stars} Stars / месяц\n"
        f"Провайдер: demo_stars\n"
        f"Checkout: <code>{checkout_hint}</code>\n\n"
        "Следующий шаг для MVP: нажми подтверждение оплаты. "
        "Позже здесь будет реальная интеграция с Telegram Stars."
    )


def render_payment_success(plan: str) -> str:
    return (
        f"Оплата подтверждена. План <b>{plan.upper()}</b> активирован.\n\n"
        "Теперь можно вернуться в меню и проверить новые лимиты и доступ к premium-функциям."
    )
