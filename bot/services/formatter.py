"""تبدیل نتایج جستجو به پیام فارسی خوانا — بدون لینک و با نتیجه باز/بسته."""

from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone

import jdatetime

from ..config import settings
from ..data.roads import Location, norm
from .search import SearchResponse, WeatherInfo

MAX_MESSAGE_LENGTH = 3800
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

_PRIORITY = ("بسته شدن", "ترافیک", "شرایط نامناسب", "عمومی")
_NEWS_LIMIT = 3

_CLOSURE_WORDS = ("بسته", "مسدود", "انسداد", "قطع", "تعطیل", "closed", "closure")
_REOPEN_WORDS = ("باز شد", "بازگشا", "آزاد شد", "reopen")
_TRAFFIC_WORDS = ("ترافیک", "شلوغ", "ازدحام", "گره", "کندی", "traffic", "jam")


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _digits(value: object) -> str:
    return str(value if value is not None else "").translate(_FA_DIGITS)


def _clean(value: str) -> str:
    """لینکها رو از متن خبر پاک میکند."""
    return _URL_RE.sub("", value or "").strip()


def _age(published: datetime | None) -> str:
    if not published:
        return "زمان نامشخص"
    now = datetime.now(timezone.utc)
    minutes = max(0, int((now - published).total_seconds() // 60))
    if minutes < 2:
        return "همین الان"
    if minutes < 60:
        return f"{_digits(minutes)} دقیقه پیش"
    hours = minutes // 60
    if hours < 24:
        return f"{_digits(hours)} ساعت پیش"
    days = hours // 24
    if days < 30:
        return f"{_digits(days)} روز پیش"
    local = jdatetime.datetime.fromgregorian(datetime=published)
    return local.strftime("%Y/%m/%d")


def _now_text() -> str:
    return _digits(jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M"))


def _weather_lines(weather: WeatherInfo | None) -> list[str]:
    if weather is None:
        return ["🌤️ <b>آب و هوا</b>", "  اطلاعاتی در دسترس نیست"]
    lines = ["🌤️ <b>آب و هوا</b>"]
    if weather.date_note:
        lines.append(f"  ⚠️ {esc(weather.date_note)}")
    main = f"  {weather.icon} همین الان: {esc(weather.description)}"
    if weather.temperature is not None:
        main += f" · 🌡️ {_digits(round(weather.temperature))} درجه"
    lines.append(main)

    if weather.day_description:
        today = f"  {weather.day_icon} {esc(weather.day_label)}: {esc(weather.day_description)}"
        if weather.temp_min is not None and weather.temp_max is not None:
            today += (
                f" · 🌡️ {_digits(round(weather.temp_min))} تا "
                f"{_digits(round(weather.temp_max))} درجه"
            )
        if weather.rain_chance is not None:
            today += f" · ☔ باران {_digits(round(weather.rain_chance))} درصد"
        lines.append(today)

    extra: list[str] = []
    if weather.wind is not None:
        extra.append(f"💨 باد {_digits(round(weather.wind))} کیلومتر/ساعت")
    if weather.humidity is not None:
        extra.append(f"💧 رطوبت {_digits(round(weather.humidity))} درصد")
    if weather.precipitation is not None:
        extra.append(f"🌧️ بارش {_digits(weather.precipitation)} میلیمتر")
    if extra:
        lines.append("  " + " · ".join(extra))
    return lines


def _road_status(response: SearchResponse) -> tuple[str, str]:
    """فقط نتیجه نهایی: باز است یا بسته (اخبار داخل پیام چاپ نمیشوند)."""
    if response.used_fallback:
        return "⚠️", "وضعیت نامشخص"

    unknown_time = datetime.min.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.recent_days)
    recent_items = [
        item
        for item in response.items
        if item.published is None or item.published >= cutoff
    ]
    if not any(item.published for item in recent_items):
        return "⚠️", "وضعیت نامشخص"

    closure: tuple[datetime, str] | None = None
    reopen: tuple[datetime, str] | None = None

    for item in recent_items:
        text = norm(f"{item.title} {item.snippet}")
        when = item.published or unknown_time

        if any(norm(word) in text for word in _REOPEN_WORDS):
            if reopen is None or when > reopen[0]:
                reopen = (when, item.title)
            continue

        if closure is None or when > closure[0]:
            for word in _CLOSURE_WORDS:
                if norm(word) in text:
                    closure = (when, item.title)
                    break

    if closure is not None and not (reopen is not None and reopen[0] > closure[0]):
        return "⛔", "جاده بسته است"

    return "✅", "جاده باز است"


def _pick_items(response: SearchResponse) -> list:
    """چند خبر مهم رو به ترتیب اهمیت انتخاب میکند — نه خیلی کم، نه خیلی زیاد."""
    unknown_time = datetime.min.replace(tzinfo=timezone.utc)
    ordered: list = []
    for category in _PRIORITY:
        group = [item for item in response.items if item.category == category]
        group.sort(key=lambda item: item.published or unknown_time, reverse=True)
        ordered.extend(group)
    return ordered[:_NEWS_LIMIT]


def _item_lines(item, detailed: bool = False) -> list[str]:
    title = esc(_clean(item.title)[:120])
    lines = [f"  • {item.icon} {title}"]
    meta = esc(_clean(item.source)) or "خبر"
    if item.published:
        meta += f" · {_age(item.published)}"
    lines.append(f"     <i>{meta}</i>")
    if detailed and item.snippet:
        snippet = esc(_clean(item.snippet)[:85])
        if snippet:
            lines.append(f"     {snippet}")
    return lines


def format_results(location: Location, response: SearchResponse, state=None) -> str:
    """همیشه یک پیام معتبر برمیگرداند — حتی اگر ورودی ناقص باشد."""
    try:
        weather_lines = _weather_lines(response.weather)
        icon, status_text = _road_status(response)
        footer = f"🕒 بروزرسانی: {_now_text()}"
        status_block = f"{icon} <b>{esc(status_text)}</b>"
        breadcrumb = esc(getattr(location, "breadcrumb", "") or "")
        header = f"📍 {breadcrumb}\n\n" if breadcrumb else ""
        return header + "\n".join(weather_lines) + "\n\n" + footer + "\n\n" + status_block
    except Exception:
        # آخرین سطح امنیتی: هیچوقت به کاربر پیام خطا نشان نده
        return (
            "🌤️ <b>آب و هوا</b>\n"
            "  اطلاعاتی در دسترس نیست\n\n"
            f"🕒 بروزرسانی: {_digits(jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M'))}\n\n"
            "⚠️ <b>وضعیت نامشخص</b>"
        )


def format_help() -> str:
    return (
        "ℹ️ <b>راهنمای RoadRadar</b>\n\n"
        "🛣️ وضعیت جادهها، ترافیک و بستهشدن مسیر را در شهرهای سراسر ایران پیدا میکنم.\n"
        "🌤️ آب و هوای الان شهر را هم نشان میدهم.\n"
        "🚦 در آخر پیام میگویم جاده باز است یا بسته.\n\n"
        "<b>دستورها:</b>\n"
        "/start — شروع و منوی اصلی\n"
        "/status — بررسی وضعیت (استان → شهر)\n"
        "/search نام شهر — جستجوی سریع، مثل <code>/search چالوس</code>\n"
        "/help — همین راهنما\n"
        "/cancel — لغو عملیات فعلی\n\n"
        "<b>جستجوی آزاد:</b>\n"
        "میتوانید مستقیم بنویسید:\n"
        "«مازندران / چالوس»\n"
        "یا «ترافیک مشهد»"
    )
