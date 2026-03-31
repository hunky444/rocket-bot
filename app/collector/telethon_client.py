from __future__ import annotations

from telethon import TelegramClient

from app.config import Settings


def build_telethon_client(settings: Settings) -> TelegramClient:
    if settings.api_id is None or not settings.api_hash:
        raise ValueError("API_ID and API_HASH must be set in .env before using Telethon collector.")

    return TelegramClient(
        session=settings.session_name,
        api_id=settings.api_id,
        api_hash=settings.api_hash,
    )
