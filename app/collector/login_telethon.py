from __future__ import annotations

import asyncio

from app.collector.gift_sync import GiftSyncService
from app.collector.telethon_client import build_telethon_client
from app.config import get_settings


async def main() -> None:
    settings = get_settings()
    client = build_telethon_client(settings)

    async with client:
        authorized = await client.is_user_authorized()
        if not authorized:
            print("Telethon session is not authorized yet.")
            print("Telegram will ask for your phone number and login code now.")
            await client.start()
            print("Login completed.")
        else:
            print("Telethon session is already authorized.")

        service = GiftSyncService(client)
        result = await service.login()
        print(result.message)


if __name__ == "__main__":
    asyncio.run(main())
