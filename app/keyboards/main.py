from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/rocket"), KeyboardButton(text="/profile")],
            [KeyboardButton(text="/leaderboard"), KeyboardButton(text="/top")],
            [KeyboardButton(text="/budget 3000"), KeyboardButton(text="/plans")],
            [KeyboardButton(text="/help")],
        ],
        resize_keyboard=True,
    )


def home_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Топ идей", callback_data="menu:top"),
                InlineKeyboardButton(text="Продажа", callback_data="menu:sell"),
            ],
            [
                InlineKeyboardButton(text="Портфель", callback_data="menu:portfolio"),
                InlineKeyboardButton(text="Алерты", callback_data="menu:alerts"),
            ],
            [
                InlineKeyboardButton(text="Профиль", callback_data="menu:profile"),
                InlineKeyboardButton(text="Ракетка", callback_data="menu:rocket"),
            ],
            [
                InlineKeyboardButton(text="Лидерборд", callback_data="menu:leaderboard"),
                InlineKeyboardButton(text="Тарифы", callback_data="menu:plans"),
            ],
        ]
    )


def plans_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Купить Pro", callback_data="checkout:pro"),
                InlineKeyboardButton(text="Купить Premium", callback_data="checkout:premium"),
            ],
            [InlineKeyboardButton(text="Назад в меню", callback_data="menu:home")],
        ]
    )


def paywall_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Открыть тарифы", callback_data="menu:plans"),
                InlineKeyboardButton(text="Назад", callback_data="menu:home"),
            ]
        ]
    )


def checkout_inline_keyboard(plan_code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить demo-оплату", callback_data=f"confirm_checkout:{plan_code}")],
            [InlineKeyboardButton(text="Назад к тарифам", callback_data="menu:plans")],
        ]
    )


def portfolio_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Добавить Plush Pepe", callback_data="portfolio_add:plush-pepe-221"),
                InlineKeyboardButton(text="Добавить Pixel Heart", callback_data="portfolio_add:pixel-heart-14"),
            ],
            [InlineKeyboardButton(text="Назад в меню", callback_data="menu:home")],
        ]
    )


def alerts_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Alert до 3000", callback_data="alert_budget:3000"),
                InlineKeyboardButton(text="Alert до 5000", callback_data="alert_budget:5000"),
            ],
            [InlineKeyboardButton(text="Назад в меню", callback_data="menu:home")],
        ]
    )


def rocket_lobby_keyboard(currency: str, auto_cashout: float | None) -> InlineKeyboardMarkup:
    if currency == "TON":
        inline_keyboard = [
            [
                InlineKeyboardButton(text="0.5 TON", callback_data="rocket:bet:TON:0.5"),
                InlineKeyboardButton(text="1 TON", callback_data="rocket:bet:TON:1"),
            ],
            [
                InlineKeyboardButton(text="2 TON", callback_data="rocket:bet:TON:2"),
                InlineKeyboardButton(text="5 TON", callback_data="rocket:bet:TON:5"),
            ],
        ]
    else:
        inline_keyboard = [
            [
                InlineKeyboardButton(text="100 Stars", callback_data="rocket:bet:XTR:100"),
                InlineKeyboardButton(text="300 Stars", callback_data="rocket:bet:XTR:300"),
            ],
            [
                InlineKeyboardButton(text="500 Stars", callback_data="rocket:bet:XTR:500"),
                InlineKeyboardButton(text="1000 Stars", callback_data="rocket:bet:XTR:1000"),
            ],
        ]

    auto_label = "Auto OFF" if auto_cashout is None else f"Auto {auto_cashout:.2f}x"
    inline_keyboard.extend(
        [
            [
                InlineKeyboardButton(text="1.50x", callback_data="rocket:auto:1.5"),
                InlineKeyboardButton(text="2.00x", callback_data="rocket:auto:2.0"),
                InlineKeyboardButton(text="3.00x", callback_data="rocket:auto:3.0"),
            ],
            [InlineKeyboardButton(text=auto_label, callback_data="rocket:auto:off")],
            [
                InlineKeyboardButton(text="Играть в Stars", callback_data="rocket:currency:XTR"),
                InlineKeyboardButton(text="Играть в TON", callback_data="rocket:currency:TON"),
            ],
            [
                InlineKeyboardButton(text="Профиль", callback_data="menu:profile"),
                InlineKeyboardButton(text="Топ игроков", callback_data="menu:leaderboard"),
            ],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def rocket_active_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Забрать выигрыш", callback_data="rocket:cashout")],
        ]
    )


def rocket_finished_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Еще раунд", callback_data="menu:rocket"),
                InlineKeyboardButton(text="Топ игроков", callback_data="menu:leaderboard"),
            ],
            [InlineKeyboardButton(text="Профиль", callback_data="menu:profile")],
        ]
    )


def profile_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="+1000 Stars", callback_data="wallet:add:XTR:1000"),
                InlineKeyboardButton(text="-500 Stars", callback_data="wallet:withdraw:XTR:500"),
            ],
            [
                InlineKeyboardButton(text="+5 TON", callback_data="wallet:add:TON:5"),
                InlineKeyboardButton(text="-2 TON", callback_data="wallet:withdraw:TON:2"),
            ],
            [
                InlineKeyboardButton(text="Сбросить демо", callback_data="wallet:reset"),
                InlineKeyboardButton(text="Лидерборд", callback_data="menu:leaderboard"),
            ],
            [InlineKeyboardButton(text="Назад в меню", callback_data="menu:home")],
        ]
    )


def leaderboard_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Играть", callback_data="menu:rocket"),
                InlineKeyboardButton(text="Профиль", callback_data="menu:profile"),
            ],
            [InlineKeyboardButton(text="Назад в меню", callback_data="menu:home")],
        ]
    )


def open_webapp_keyboard(webapp_url: str, user_id: int) -> InlineKeyboardMarkup:
    separator = "&" if "?" in webapp_url else "?"
    final_url = f"{webapp_url}{separator}user_id={user_id}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Open WebApp", web_app=WebAppInfo(url=final_url))],
            [InlineKeyboardButton(text="Остаться в Telegram-режиме", callback_data="menu:rocket")],
        ]
    )
