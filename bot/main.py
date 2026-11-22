"""نقطه ورود بات RoadRadar."""

from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from .config import settings
from .handlers import commands, flow

log = logging.getLogger("road_radar")


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    log.info("RoadRadar bot is starting ...")

    bot = Bot(
        token=settings.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(commands.router)
    dp.include_router(flow.router)

    # روی هاستهایی مثل Render متغیر PORT تنظیم میشود؛ سرور ساده HTTP همیشه
    # پاسخ میدهد تا سرویس توسط سیستم خوابانده نشود.
    runner = None
    port = int(os.getenv("PORT", "0") or 0)
    if port:
        from .webserver import start_webserver

        runner = await start_webserver(port)
        log.info("Health server listening on port %s", port)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        if runner is not None:
            await runner.cleanup()
        await bot.session.close()


def run() -> None:
    if not settings.token or ":" not in settings.token:
        raise SystemExit(
            "❌ توکن بات پیدا نشد. فایل .env را از .env.example کپی کنید "
            "و BOT_TOKEN را با توکن دریافتی از @BotFather پر کنید."
        )
    asyncio.run(main())


if __name__ == "__main__":
    run()
