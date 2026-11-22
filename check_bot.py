"""بررسی سریع توکن، مشخصات و عکس پروفایل بات (بدون چاپ توکن)."""

from __future__ import annotations

import asyncio

import httpx

from bot.config import settings


async def main() -> None:
    if not settings.token or settings.token.startswith("123456789:"):
        print("❌ هنوز توکن واقعی را در فایل .env وارد نکردهاید.")
        return

    async with httpx.AsyncClient(timeout=15) as client:
        base = f"https://api.telegram.org/bot{settings.token}"

        me = (await client.get(f"{base}/getMe")).json()
        if not me.get("ok"):
            print("❌ توکن معتبر نیست:", me.get("description"))
            return

        bot = me["result"]
        print("✅ توکن معتبر است")
        print("   نام بات:", bot.get("first_name"))
        print("   یوزرنیم:", "@" + bot["username"])

        photos = (await client.get(f"{base}/getUserProfilePhotos", params={"user_id": bot["id"]})).json()
        if photos.get("ok"):
            count = photos["result"].get("total_count", 0)
            print("🖼️ عکس پروفایل:", f"بله ({count} عکس)" if count else "خیر — هنوز عکسی گذاشته نشده")
        else:
            print("⚠️ بررسی عکس پروفایل ناموفق بود:", photos.get("description"))


if __name__ == "__main__":
    asyncio.run(main())
