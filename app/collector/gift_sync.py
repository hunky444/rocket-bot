from __future__ import annotations

from dataclasses import dataclass

from telethon import TelegramClient


@dataclass(slots=True)
class SyncResult:
    ok: bool
    message: str


class GiftSyncService:
    def __init__(self, client: TelegramClient) -> None:
        self._client = client

    async def login(self) -> SyncResult:
        await self._client.connect()
        if await self._client.is_user_authorized():
            return SyncResult(ok=True, message="Telethon session already authorized.")

        return SyncResult(
            ok=False,
            message=(
                "Telethon client is not authorized yet. "
                "Run the interactive login script first to enter your phone number and Telegram code."
            ),
        )

    async def sync_available_gifts(self) -> SyncResult:
        # This is a safe starting stub. The next implementation step is to call
        # payments.getStarGifts / related objects and map them into the local DB.
        if not await self._client.is_user_authorized():
            return SyncResult(ok=False, message="Telethon session is not authorized.")
        return SyncResult(
            ok=True,
            message=(
                "Collector scaffold is ready. "
                "Next step is wiring real Telegram gift methods into the repository."
            ),
        )
