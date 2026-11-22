"""تبدیل نتایج جستجو به پیام فارسی خوانا برای تلگرام."""

from __future__ import annotations

import html
from datetime import datetime, timezone

import jdatetime

from ..data.roads import Location
from .search import CATEGORY_ORDER, CATEGORY_ICONS, SearchResponse

MAX_MESSAGE_LENGTH = 3800


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _age(published: datetime | None) -> str:
    if not published:
        return "زمان نامشخص"
    now = datetime.now(timezone.utc)
    minutes = max(0, int((now - published).total_seconds() // 60))
    if minutes < 2:
        return "همین الان"
    if minutes < 60:
        return f"{minutes} دقیقه پیش"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} ساعت پیش"
    days = hours // 24
    if days < 30:
        return f"{days} روز پیش"
    local = jdatetime.datetime.fromgregorian(datetime=published)
    return local.strftime("%Y/%m/%d")


def _now_text() -> str:
    return jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M")


def _item_lines(item) -> list[str]:
    title = esc(item.title)
    if item.url:
        line = f'  • <a href="{esc(item.url)}">{title}</a>'
    else:
        line = f"  • {title}"
    lines = [line]
    meta = f"{esc(item.source)} · {_age(item.published)}"
    if item.snippet:
        meta += f"\n    {esc(item.snippet[:150])}"
    lines.append(f"    <i>{meta}</i>")
    return lines


def format_results(location: Location, response: SearchResponse) -> str:
    count = len(response.items)
    report_word = "ذخیرهشده" if response.used_fallback else "تازه"
    header = (
        "🛣️ <b>وضعیت جاده</b>\n"
        f"📍 {esc(location.breadcrumb)}\n"
        f"🔎 {count} گزارش {report_word} پیدا شد\n"
    )
    if response.used_fallback:
        header += (
            "\n⚠️ نتوانستم از وب گزارشی پیدا کنم (احتمالاً قطعی ارتباط)، "
            "پس نمونه ذخیرهشده نشان میدهم.\n"
        )

    footer = (
        f"\n──────────\n🕒 بروزرسانی: {_now_text()}"
        "\n🔄 برای بروزرسانی، دوباره دکمه «بررسی وضعیت» را بزنید."
    )

    grouped: dict[str, list] = {category: [] for category in CATEGORY_ORDER}
    for item in response.items:
        grouped.setdefault(item.category, []).append(item)

    blocks: list[str] = []
    for category in CATEGORY_ORDER:
        items = grouped.get(category) or []
        if not items:
            continue
        lines = [f"{CATEGORY_ICONS.get(category, 'ℹ️')} <b>{esc(category)}</b>"]
        for item in items:
            candidate = lines + _item_lines(item)
            assembled = header + "\n\n".join([*blocks, "\n".join(candidate)]) + footer
            if len(assembled) > MAX_MESSAGE_LENGTH:
                break
            lines = candidate
        if len(lines) > 1:
            blocks.append("\n".join(lines))

    return header + "\n\n".join(blocks) + footer


def format_help() -> str:
    return (
        "ℹ️ <b>راهنمای RoadRadar</b>\n\n"
        "🛣️ وضعیت جادهها، ترافیک، تصادف، بستهشدن مسیر و شرایط نامناسب "
        "را برای مسیرهای شمال ایران پیدا میکنم.\n\n"
        "<b>دستورها:</b>\n"
        "/start — شروع و منوی اصلی\n"
        "/status — بررسی وضعیت جاده (گام به گام)\n"
        "/search عبارت — جستجوی سریع، مثل <code>/search جاده چالوس ترافیک</code>\n"
        "/help — همین راهنما\n"
        "/cancel — لغو عملیات فعلی\n\n"
        "<b>جستجوی آزاد:</b>\n"
        "میتوانید مستقیم بنویسید:\n"
        "«مازندران / چالوس / جاده چالوس»\n"
        "یا «ترافیک جاده هراز امروز»\n\n"
        "📰 منابع: اخبار Google News و Bing News (بدون نیاز به کلید API). "
        "اگر وب در دسترس نباشد، وضعیت نمونه ذخیرهشده نشان داده میشود."
    )
