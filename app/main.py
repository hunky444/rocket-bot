import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.handlers import register_handlers
from app.services.container import repository, settings
from app.webapp.server import start_webapp_server


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    repository.init_schema()
    if not repository.has_market_snapshots():
        repository.seed_market_snapshots()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    register_handlers(dp)
    web_runner = await start_webapp_server()
    try:
        await dp.start_polling(bot)
    finally:
        await web_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
