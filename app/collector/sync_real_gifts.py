from __future__ import annotations

import asyncio
import re
from pathlib import Path

from telethon import functions

from app.collector.telethon_client import build_telethon_client
from app.config import get_settings
from app.services.repository import Repository


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return cleaned.strip("-") or "gift"


async def main() -> None:
    settings = get_settings()
    repository = Repository(settings.database_path)
    repository.init_schema()

    assets_dir = Path(settings.assets_dir) / "gifts"
    assets_dir.mkdir(parents=True, exist_ok=True)

    client = build_telethon_client(settings)
    async with client:
        result = await client(functions.payments.GetStarGiftsRequest(hash=0))
        rows: list[dict[str, object]] = []

        for gift in getattr(result, "gifts", []):
            title = getattr(gift, "title", None) or f"Gift #{gift.id}"
            slug = f"{slugify(title)}-{gift.id}"

            image_path = ""
            try:
                downloaded = await client.download_media(gift.sticker, file=str(assets_dir / slug))
                if downloaded:
                    image_path = str(Path(downloaded).resolve())
            except Exception:
                image_path = ""

            price_stars = int(getattr(gift, "stars", 0) or 0)
            resell_min_stars = int(getattr(gift, "resell_min_stars", 0) or 0)
            availability_remains = getattr(gift, "availability_remains", None)
            availability_total = getattr(gift, "availability_total", None)

            comment_parts: list[str] = []
            if getattr(gift, "limited", False):
                if availability_remains is not None and availability_total is not None:
                    comment_parts.append(f"Лимитированный подарок: осталось {availability_remains} из {availability_total}")
                else:
                    comment_parts.append("Лимитированный подарок")
            if getattr(gift, "sold_out", False):
                comment_parts.append("Сейчас sold out")
            if not comment_parts:
                comment_parts.append("Доступный подарок из Telegram")

            rows.append(
                {
                    "gift_slug": slug,
                    "title": title,
                    "model": title,
                    "backdrop": "Base gift",
                    "image_url": "",
                    "image_path": image_path,
                    "price_stars": price_stars,
                    "price_ton": 0.0,
                    "median_stars": resell_min_stars if resell_min_stars > 0 else price_stars,
                    "median_ton": 0.0,
                    "liquidity": "high" if getattr(gift, "limited", False) else "medium",
                    "risk": "medium" if getattr(gift, "sold_out", False) else "low",
                    "comment": ". ".join(comment_parts),
                    "source_name": "telegram_getStarGifts",
                    "updated_at": repository._utc_now_iso(),
                }
            )

        if rows:
            repository.replace_market_snapshots(rows)
            print(f"Synced {len(rows)} gifts into market_snapshots.")
        else:
            print("No gifts returned from Telegram.")


if __name__ == "__main__":
    asyncio.run(main())
