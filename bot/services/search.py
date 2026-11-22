"""جستجوی خودکار وب (بدون نیاز به API Key) برای وضعیت جادها."""

from __future__ import annotations

import asyncio
import html
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import parse_qs, quote, unquote, urlparse

import httpx
import jdatetime

from ..config import settings
from ..data.roads import Location, find_road, norm

log = logging.getLogger(__name__)

CATEGORY_ORDER = ("ترافیک", "بسته شدن", "شرایط نامناسب", "عمومی")
CATEGORY_ICONS = {
    "ترافیک": "🚗",
    "بسته شدن": "🚧",
    "شرایط نامناسب": "⛈️",
    "عمومی": "ℹ️",
}
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "بسته شدن": (
        "بسته", "مسدود", "انسداد", "قطع", "تجاوز از ظرفیت", "تعطیلی", "بسته شدن",
        "closed", "closure",
    ),
    "شرایط نامناسب": (
        "برف", "باران", "یخبندان", "لغزنده", "لغزندگی", "مه", "کولاک", "رانش",
        "سیل", "طوفان", "گرد و غبار", "گردوغبار", "مه آلود", "مه گرفته",
        "weather", "snow", "rain",
    ),
    "ترافیک": (
        "ترافیک", "شلوغ", "ازدحام", "گره ترافیک", "کندی", "صف خودرو", "دلدل",
        "traffic", "jam",
    ),
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.7",
}

# مختصات تقریبی شهرها و استانها فقط برای گرفتن آب و هوا (بدون کلید API)
CITY_COORDS: dict[str, tuple[float, float]] = {
    "رشت": (37.2808, 49.5832),
    "لاهیجان": (37.2065, 49.9486),
    "بندر انزلی": (37.4693, 49.4597),
    "آستارا": (38.2494, 48.6781),
    "رودسر": (37.0539, 50.3453),
    "منجیل": (36.6278, 49.6386),
    "تالش": (37.7989, 48.9127),
    "فومن": (37.2294, 49.2881),
    "چالوس": (36.6557, 51.1973),
    "آمل": (36.4681, 52.3486),
    "ساری": (36.5633, 53.0607),
    "نوشهر": (36.6508, 51.4925),
    "محمودآباد": (36.6256, 52.2581),
    "بابُل": (36.5582, 52.6755),
    "بابلسر": (36.7144, 52.6586),
    "قائمشهر": (36.4618, 52.8387),
    "رامسر": (36.9108, 50.6568),
    "تنکابن": (36.8193, 50.8717),
    "بهشهر": (36.6947, 53.5437),
    "سوادکوه": (36.0853, 53.0000),
    "گرگان": (36.8443, 54.4383),
    "گنبدکاووس": (37.2475, 55.1454),
    "بندرترکمن": (36.8689, 54.0672),
    "علیآباد کتول": (36.9077, 54.8358),
    "مینودشت": (37.4000, 55.0000),
    "کلاله": (37.4667, 55.5500),
    "سمنان": (35.5729, 53.3970),
    "شاهرود": (36.4186, 55.0135),
    "دامغان": (36.1692, 54.3510),
    "گرمسار": (35.2092, 52.3350),
    "فیروزکوه": (35.7761, 52.7742),
    "قزوین": (36.2687, 50.0043),
    "تاکستان": (36.4667, 49.4667),
    "آبیک": (36.1694, 50.0208),
    "بوئینزهرا": (35.9242, 49.7064),
    "کرج": (35.8327, 50.9916),
    "فردیس": (35.7522, 50.9778),
    "هشتگرد": (35.7828, 50.6903),
    "ساوجبلاغ": (35.7844, 50.6081),
    "اشتهارد": (35.6828, 50.3586),
    "تهران": (35.6892, 51.3890),
    "شمیرانات": (35.8100, 51.4400),
    "دماوند": (35.7236, 52.0685),
    "ری": (35.5833, 51.4333),
    "اردبیل": (38.2498, 48.2933),
    "مشگینشهر": (38.4069, 47.6811),
    "خلخال": (38.2100, 48.5300),
    "پارسآباد": (39.3839, 47.4950),
    "سرعین": (38.3000, 48.1000),
    "تبریز": (38.0792, 46.2919),
    "مراغه": (37.3924, 46.0386),
    "میاندوآب": (37.0439, 46.0927),
    "اهر": (38.4857, 47.0772),
    "ارومیه": (37.5527, 45.0761),
    "خوی": (38.5517, 44.9382),
    "سلماس": (38.1834, 44.8799),
    "مهاباد": (36.7069, 45.7210),
    "بوکان": (36.8606, 46.2867),
    "اصفهان": (32.6572, 51.6773),
    "کاشان": (33.9890, 51.4442),
    "نجفآباد": (32.6289, 51.3183),
    "خمینی شهر": (32.6750, 51.5450),
    "ایلام": (33.6374, 46.4225),
    "مهران": (33.1211, 46.1883),
    "دهلران": (32.6833, 47.8167),
    "بوشهر": (28.9234, 50.8203),
    "بندر گناوه": (29.5911, 50.3700),
    "دیر": (28.8347, 51.5597),
    "شهرکرد": (32.3285, 50.8644),
    "بروجن": (31.9633, 51.2944),
    "بیرجند": (32.8663, 59.2211),
    "قائن": (33.7500, 59.1800),
    "مشهد": (36.2972, 59.6067),
    "نیشابور": (36.2089, 58.7956),
    "سبزوار": (36.2136, 57.6778),
    "تربت حیدریه": (35.2742, 59.2195),
    "بجنورد": (37.4713, 57.3281),
    "شیروان": (37.4000, 58.0000),
    "اهواز": (31.3183, 48.6706),
    "آبادان": (30.3449, 48.6781),
    "خرمشهر": (30.4278, 48.1853),
    "دزفول": (32.4200, 48.4100),
    "زنجان": (36.6734, 48.4787),
    "ابهر": (36.1600, 49.1700),
    "زاهدان": (29.4963, 60.8629),
    "چابهار": (25.2836, 60.6441),
    "زابل": (30.6700, 61.4900),
    "شیراز": (29.5918, 52.5837),
    "مرودشت": (29.8700, 52.7900),
    "کازرون": (29.6200, 51.6500),
    "جهرم": (28.5000, 53.0600),
    "قم": (34.6416, 50.8746),
    "سنندج": (35.3141, 46.9957),
    "سقز": (36.1500, 46.2667),
    "بانه": (36.0000, 46.3000),
    "کرمان": (30.2839, 57.0834),
    "سیرجان": (29.9200, 55.6800),
    "بم": (29.1000, 58.3600),
    "رفسنجان": (30.4000, 55.9900),
    "کرمانشاه": (34.3142, 47.0650),
    "اسلامآباد غرب": (34.0900, 46.4200),
    "پاوه": (35.0900, 46.4200),
    "یاسوج": (30.6686, 51.5875),
    "دوگنبدان": (30.3500, 50.4700),
    "خرمآباد": (33.4875, 48.3557),
    "بروجرد": (33.8958, 48.7636),
    "دورود": (33.4947, 48.9964),
    "اراک": (34.0915, 49.6892),
    "ساوه": (35.0200, 50.3600),
    "خمین": (34.1300, 49.4600),
    "بندرعباس": (27.1832, 56.2666),
    "بندر لنگه": (26.8700, 55.2900),
    "میناب": (25.7600, 57.0900),
    "همدان": (34.7992, 48.5146),
    "ملایر": (34.3300, 48.7400),
    "نهاوند": (34.2000, 48.3800),
    "یزد": (31.8974, 54.3569),
    "میبد": (32.3000, 54.0700),
    "اردکان": (32.3200, 53.7700),
}

PROVINCE_COORDS: dict[str, tuple[float, float]] = {
    "گیلان": CITY_COORDS["رشت"],
    "مازندران": CITY_COORDS["ساری"],
    "گلستان": CITY_COORDS["گرگان"],
    "سمنان": CITY_COORDS["سمنان"],
    "قزوین": CITY_COORDS["قزوین"],
    "البرز": CITY_COORDS["کرج"],
    "تهران": CITY_COORDS["تهران"],
    "اردبیل": CITY_COORDS["اردبیل"],
    "آذربایجان شرقی": CITY_COORDS["تبریز"],
    "آذربایجان غربی": CITY_COORDS["ارومیه"],
    "اصفهان": CITY_COORDS["اصفهان"],
    "ایلام": CITY_COORDS["ایلام"],
    "بوشهر": CITY_COORDS["بوشهر"],
    "چهارمحال و بختیاری": CITY_COORDS["شهرکرد"],
    "خراسان جنوبی": CITY_COORDS["بیرجند"],
    "خراسان رضوی": CITY_COORDS["مشهد"],
    "خراسان شمالی": CITY_COORDS["بجنورد"],
    "خوزستان": CITY_COORDS["اهواز"],
    "زنجان": CITY_COORDS["زنجان"],
    "سیستان و بلوچستان": CITY_COORDS["زاهدان"],
    "فارس": CITY_COORDS["شیراز"],
    "قم": CITY_COORDS["قم"],
    "کردستان": CITY_COORDS["سنندج"],
    "کرمان": CITY_COORDS["کرمان"],
    "کرمانشاه": CITY_COORDS["کرمانشاه"],
    "کهگیلویه و بویراحمد": CITY_COORDS["یاسوج"],
    "لرستان": CITY_COORDS["خرمآباد"],
    "مرکزی": CITY_COORDS["اراک"],
    "هرمزگان": CITY_COORDS["بندرعباس"],
    "همدان": CITY_COORDS["همدان"],
    "یزد": CITY_COORDS["یزد"],
}

_CITY_LOOKUP = {norm(name): coords for name, coords in CITY_COORDS.items()}
_PROVINCE_LOOKUP = {norm(name): coords for name, coords in PROVINCE_COORDS.items()}

_WEATHER_CODES: dict[int, tuple[str, str]] = {
    0: ("☀️", "آفتابی"),
    1: ("🌤️", "عمدتاً آفتابی"),
    2: ("⛅", "نیمه ابری"),
    3: ("☁️", "ابری"),
    45: ("🌫️", "مه"),
    48: ("🌫️", "مه یخبندان"),
    51: ("🌦️", "نم باران خفیف"),
    53: ("🌦️", "نم باران"),
    55: ("🌦️", "نم باران شدید"),
    56: ("🌧️", "نم باران یخبندان"),
    57: ("🌧️", "نم باران یخبندان شدید"),
    61: ("🌧️", "باران خفیف"),
    63: ("🌧️", "باران"),
    65: ("🌧️", "باران شدید"),
    66: ("🌧️", "باران یخبندان"),
    67: ("🌧️", "باران یخبندان شدید"),
    71: ("❄️", "برف خفیف"),
    73: ("❄️", "برف"),
    75: ("❄️", "برف شدید"),
    77: ("❄️", "دانه برف"),
    80: ("🌦️", "رگبار خفیف"),
    81: ("🌦️", "رگبار"),
    82: ("⛈️", "رگبار شدید"),
    85: ("🌨️", "رگبار برف"),
    86: ("🌨️", "رگبار برف شدید"),
    95: ("⛈️", "رعد و برق"),
    96: ("⛈️", "رعد و برق و تگرگ"),
    99: ("⛈️", "رعد و برق و تگرگ شدید"),
}


@dataclass
class WeatherInfo:
    icon: str
    description: str
    temperature: float | None = None
    humidity: int | None = None
    wind: float | None = None
    precipitation: float | None = None
    day_label: str = "امروز"
    day_icon: str = "🌤️"
    day_description: str = ""
    date_note: str = ""
    temp_max: float | None = None
    temp_min: float | None = None
    rain_chance: int | None = None


_FA_TO_EN = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
_WEEKDAYS = (
    "شنبه", "یکشنبه", "دوشنبه", "سهشنبه", "چهارشنبه", "پنجشنبه", "جمعه",
)


def _day_label(index: int, times: list[str], word: str) -> str:
    return word


def _resolve_day(date_text: str | None, times: list[str]) -> tuple[int, str, str]:
    """تاریخ نوشتهشده کاربر رو به یکی از روزهای پیشبینی تبدیل میکند."""
    if not times:
        return 0, "امروز", ""

    raw = (date_text or "").strip()
    key = norm(raw.translate(_FA_TO_EN))

    if not key or key in ("امروز", "الان", "همین الان", "فعلا"):
        return 0, _day_label(0, times, "امروز"), ""
    if key in ("فردا", "روز بعد"):
        return 1, _day_label(1, times, "فردا"), ""
    if key in ("پس فردا", "پسفردا"):
        return 2, _day_label(2, times, "پسفردا"), ""

    # نام روز هفته؛ مثلاً «دوشنبه» یا «سهشنبه»
    for index, value in enumerate(times[:7]):
        try:
            greg = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            continue
        jd = jdatetime.date.fromgregorian(date=greg)
        if norm(jd.strftime("%A")) == key:
            return index, _day_label(index, times, raw[:20]), ""

    # تاریخ مشخص؛ مثلاً ۱۴۰۵/۰۹/۲۵
    cleaned = raw.translate(_FA_TO_EN).replace(" ", "")
    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            jd = jdatetime.datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
        target = jd.togregorian().isoformat()
        if target in times:
            index = times.index(target)
            return index, _day_label(index, times, jd.strftime("%d %B")), ""
        return (
            0,
            _day_label(0, times, "امروز"),
            "این تاریخ خارج از پیشبینی ۷ روزه است؛ وضعیت امروز نشان داده شد.",
        )

    return (
        0,
        _day_label(0, times, "امروز"),
        "تاریخ را متوجه نشدم؛ وضعیت امروز نشان داده شد.",
    )


def _coords_for(location: Location) -> tuple[float, float] | None:
    for value in (location.city, location.province, location.free_query):
        if not value:
            continue
        key = norm(value)
        if not key:
            continue
        if key in _CITY_LOOKUP:
            return _CITY_LOOKUP[key]
        if key in _PROVINCE_LOOKUP:
            return _PROVINCE_LOOKUP[key]
        for name, coords in _CITY_LOOKUP.items():
            if len(key) >= 4 and len(name) >= 4 and (key in name or name in key):
                return coords
    return None


async def _fetch_weather(
    client: httpx.AsyncClient,
    coords: tuple[float, float],
    date_text: str | None = None,
) -> WeatherInfo | None:
    try:
        response = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": coords[0],
                "longitude": coords[1],
                "current": (
                    "temperature_2m,relative_humidity_2m,"
                    "precipitation,weather_code,wind_speed_10m"
                ),
                "daily": (
                    "weather_code,temperature_2m_max,temperature_2m_min,"
                    "precipitation_probability_max"
                ),
                "timezone": "Asia/Tehran",
                "forecast_days": 7,
            },
        )
        response.raise_for_status()
        payload = response.json()
        current = payload.get("current") or {}
        daily = payload.get("daily") or {}
    except Exception as exc:
        log.debug("Weather fetch failed: %s", exc)
        return None

    icon, description = _WEATHER_CODES.get(
        current.get("weather_code"), ("🌤️", "وضعیت عادی")
    )
    times = list(daily.get("time") or [])
    index, day_label, date_note = _resolve_day(date_text, times)

    def _daily(key: str):
        values = daily.get(key) or []
        return values[index] if len(values) > index else None

    day_icon, day_description = _WEATHER_CODES.get(
        _daily("weather_code"), ("🌤️", "وضعیت عادی")
    )
    return WeatherInfo(
        icon=icon,
        description=description,
        temperature=current.get("temperature_2m"),
        humidity=current.get("relative_humidity_2m"),
        wind=current.get("wind_speed_10m"),
        precipitation=current.get("precipitation"),
        day_label=day_label,
        day_icon=day_icon,
        day_description=day_description,
        date_note=date_note,
        temp_max=_daily("temperature_2m_max"),
        temp_min=_daily("temperature_2m_min"),
        rain_chance=_daily("precipitation_probability_max"),
    )


_WTTR_WEATHER = {
    "sunny": ("☀️", "آفتابی"),
    "clear": ("☀️", "صاف"),
    "partly cloudy": ("⛅", "نیمه ابری"),
    "cloudy": ("☁️", "ابری"),
    "overcast": ("☁️", "ابری"),
    "mist": ("🌫️", "مه"),
    "fog": ("🌫️", "مه"),
    "patchy light fog": ("🌫️", "مه"),
    "light rain": ("🌧️", "باران خفیف"),
    "rain": ("🌧️", "بارانی"),
    "heavy rain": ("🌧️", "باران شدید"),
    "patchy rain nearby": ("🌦️", "رگبار پراکنده"),
    "light drizzle": ("🌦️", "نم نم باران"),
    "drizzle": ("🌦️", "نم نم باران"),
    "snow": ("❄️", "برفی"),
    "light snow": ("❄️", "برف خفیف"),
    "heavy snow": ("❄️", "برف شدید"),
    "thunder": ("⛈️", "رعد و برق"),
    "thundery outbreaks nearby": ("⛈️", "رعد و برق"),
    "blizzard": ("❄️", "کولاک"),
    "smoky haze": ("🌫️", "مه آلود"),
    "haze": ("🌫️", "مه آلود"),
    "light rain shower": ("🌦️", "رگبار خفیف"),
    "rain shower": ("🌦️", "رگبار"),
    "patchy light rain with thunder": ("⛈️", "رعد و برق"),
}


def _wttr_desc(value: str) -> tuple[str, str]:
    key = (value or "").strip().lower()
    if key in _WTTR_WEATHER:
        return _WTTR_WEATHER[key]
    for word, pair in _WTTR_WEATHER.items():
        if word in key:
            return pair
    return "🌤️", value or "وضعیت عادی"


def _num(value, cast=float):
    try:
        return cast(str(value).strip())
    except (ValueError, TypeError):
        return None


_GEO_ALIASES = {"بندرعباس": "بندر عباس"}


async def _geocode(client: httpx.AsyncClient, name: str) -> tuple[float, float] | None:
    """اسم شهر رو تو سایت جئوکدینگ پیدا میکند و مختصاتش رو میدهد."""
    candidates = [name]
    alias = _GEO_ALIASES.get(name.strip())
    if alias and alias not in candidates:
        candidates.append(alias)

    for candidate in candidates:
        for lang in ("fa", "en"):
            try:
                r = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": candidate, "count": 3, "language": lang, "format": "json"},
                )
                r.raise_for_status()
                for hit in r.json().get("results") or []:
                    lat, lon = hit.get("latitude"), hit.get("longitude")
                    if lat is not None and lon is not None:
                        return float(lat), float(lon)
            except Exception as exc:
                log.debug("Geocode failed (%s, %s): %s", candidate, lang, exc)
    return None


async def _fetch_wttr(
    client: httpx.AsyncClient, name: str, date_text: str | None
) -> WeatherInfo | None:
    """منبع دوم آب و هوا — با خود اسم شهر کار میکند."""
    try:
        r = await client.get(
            "https://wttr.in/" + quote(name.strip()),
            params={"format": "j1", "lang": "fa"},
        )
        r.raise_for_status()
        payload = r.json()
    except Exception as exc:
        log.debug("wttr.in failed for %s: %s", name, exc)
        return None

    current = (payload.get("current_condition") or [{}])[0]
    if not current:
        return None

    icon, description = _wttr_desc(
        (current.get("weatherDesc") or [{}])[0].get("value") or ""
    )
    daily_raw = payload.get("weather") or []
    times = [str(d.get("date")) for d in daily_raw if d.get("date")]
    index, day_label, date_note = _resolve_day(date_text, times)
    day = daily_raw[index] if index < len(daily_raw) else {}

    hourly = day.get("hourly") or []
    noon = hourly[len(hourly) // 2] if hourly else {}
    if noon:
        day_icon, day_description = _wttr_desc(
            (noon.get("weatherDesc") or [{}])[0].get("value") or ""
        )
    else:
        day_icon, day_description = icon, description

    return WeatherInfo(
        icon=icon,
        description=description,
        temperature=_num(current.get("temp_C")),
        humidity=_num(current.get("humidity"), int),
        wind=_num(current.get("windspeedKmph")),
        precipitation=_num(current.get("precipMM")),
        day_label=day_label,
        day_icon=day_icon,
        day_description=day_description,
        date_note=date_note,
        temp_max=_num(day.get("maxtempC")),
        temp_min=_num(day.get("mintempC")),
        rain_chance=_num(noon.get("chanceofrain"), int),
    )


async def weather_only(location: Location) -> WeatherInfo | None:
    """چند منبع پشت سر هم: مختصات ذخیرهشده → جئوکدینگ → سایت دوم هوا."""
    date_text = getattr(location, "date_text", None)
    names = [
        value.strip()
        for value in (location.city, location.province, location.free_query)
        if value and value.strip()
    ]

    client = httpx.AsyncClient(
        timeout=max(settings.search_timeout, 15),
        headers=_HEADERS,
        follow_redirects=True,
    )
    try:
        # ۱) مختصات ذخیرهشده
        coords = _coords_for(location)
        if coords:
            for _ in range(2):
                try:
                    found = await _fetch_weather(client, coords, date_text)
                    if found is not None:
                        return found
                except Exception as exc:
                    log.debug("Weather coords attempt failed: %s", exc)

        # ۲) جستجوی اسم شهر در سایت جئوکدینگ
        for name in names:
            geo = await _geocode(client, name)
            if geo is None:
                continue
            for _ in range(2):
                try:
                    found = await _fetch_weather(client, geo, date_text)
                    if found is not None:
                        return found
                except Exception as exc:
                    log.debug("Weather geocode attempt failed: %s", exc)

        # ۳) سایت دوم آب و هوا
        for name in names:
            found = await _fetch_wttr(client, name, date_text)
            if found is not None:
                return found
    finally:
        await client.aclose()
    return None


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    published: datetime | None
    snippet: str
    category: str
    provider: str

    @property
    def icon(self) -> str:
        return CATEGORY_ICONS.get(self.category, "ℹ️")


@dataclass
class SearchResponse:
    items: list[NewsItem]
    queries: list[str]
    used_fallback: bool
    total_found: int
    weather: WeatherInfo | None = None


def _clean_url(url: str) -> str:
    """لینکهای واسطه Bing را به آدرس اصلی خبر تبدیل میکند."""
    try:
        parsed = urlparse(url)
        if "bing.com" in parsed.netloc:
            target = parse_qs(parsed.query).get("url", [None])[0]
            if target:
                return unquote(target)
    except (ValueError, TypeError):
        pass
    return url


def _strip_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def _detect_category(text: str) -> str:
    value = norm(text)
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if norm(keyword) in value:
                return category
    return "عمومی"


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (TypeError, ValueError, IndexError):
        return None


def _child_text(node: ET.Element, tag: str) -> str:
    child = node.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _find_source(node: ET.Element) -> str:
    child = node.find("source")
    if child is None:
        for sub in node:
            # برخی فیدها از namespace مثل News:Source استفاده میکنند
            if sub.tag.lower().endswith("source"):
                child = sub
                break
    if child is None:
        return ""
    return (child.text or "").strip() or child.attrib.get("url", "")


def _parse_rss(payload: str, provider: str) -> list[NewsItem]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        log.warning("RSS parse error (%s): %s", provider, exc)
        return []

    items: list[NewsItem] = []
    for node in root.findall(".//item"):
        title = _strip_html(_child_text(node, "title"))
        url = _child_text(node, "link")
        source = _find_source(node)
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3].strip()
        snippet = _strip_html(_child_text(node, "description"))[:260]
        published = _parse_date(_child_text(node, "pubDate"))
        if not title or not url:
            continue
        items.append(
            NewsItem(
                title=title,
                url=_clean_url(url),
                source=source or provider,
                published=published,
                snippet=snippet,
                category=_detect_category(f"{title} {snippet}"),
                provider=provider,
            )
        )
    return items


async def _fetch_google(client: httpx.AsyncClient, query: str) -> list[NewsItem]:
    response = await client.get(
        "https://news.google.com/rss/search",
        params={"q": query, "hl": "fa", "gl": "IR", "ceid": "IR:fa"},
    )
    response.raise_for_status()
    return _parse_rss(response.text, "Google News")


async def _fetch_bing(client: httpx.AsyncClient, query: str) -> list[NewsItem]:
    response = await client.get(
        "https://www.bing.com/news/search",
        params={"q": query, "format": "rss", "setlang": "fa-IR", "cc": "IR"},
    )
    response.raise_for_status()
    return _parse_rss(response.text, "Bing News")


def _search_target(location: Location) -> str:
    """کوتاهترین نام قابل جستجو را برای جاده انتخاب میکند."""
    if location.road:
        road = find_road(location.road)
        if road:
            aliases = [name for name in road.aliases if 8 <= len(name) <= 20]
            if aliases:
                return aliases[0]
            return re.sub(r"\s*\([^)]*\)", "", road.name).strip()
    target = location.city or location.province or "جاده"
    return re.sub(r"\s*\([^)]*\)", "", target).strip()


def build_queries(location: Location) -> list[str]:
    if location.free_query:
        return [location.free_query.strip()]

    target = _search_target(location)
    queries = [target, f"{target} ترافیک", f"{target} بسته شدن"]
    return list(dict.fromkeys(queries))[:3]


def _dedupe(items: Iterable[NewsItem]) -> list[NewsItem]:
    seen: set[str] = set()
    result: list[NewsItem] = []
    for item in items:
        key = norm(item.title)[:90]
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


_ROAD_TERMS = tuple(norm(word) for word in (
    "جاده", "ترافیک", "راه", "مسیر", "رانندگی", "خودرو", "راهداری",
))


def _is_relevant(item: NewsItem, location: Location) -> bool:
    if location.free_query:
        return True
    # خبر فقط وقتی مربوط به همان محل باشد — خبر استان/جاده دیگری نباید بیاید
    text = norm(f"{item.title} {item.snippet}")
    for value in (location.target, location.city, location.province):
        if value and norm(value) in text:
            return True
    return False


_ACCIDENT_TERMS = tuple(norm(word) for word in (
    "تصادف", "سانحه", "حادثه", "واژگون", "برخورد", "مجروح", "کشته", "فوت",
    "accident", "crash",
))


def _is_accident(item: NewsItem) -> bool:
    """اخبار تصادف کاملاً حذف میشوند — حتی اگر دستهبندی دیگری خورده باشند."""
    text = norm(f"{item.title} {item.snippet}")
    return any(term in text for term in _ACCIDENT_TERMS)


def _rank(items: list[NewsItem], location: Location) -> list[NewsItem]:
    now = datetime.now(timezone.utc)
    terms = [norm(value) for value in (location.target, location.city, location.province) if value]
    cutoff = now - timedelta(days=settings.recent_days)

    def score(item: NewsItem) -> float:
        value = 0.0
        if item.published:
            if item.published >= cutoff:
                value += 25.0
            hours = max(0.0, (now - item.published).total_seconds() / 3600)
            value += max(0.0, 20.0 - hours / 12)
        text = norm(f"{item.title} {item.snippet}")
        for term in set(terms):
            if term and term in text:
                value += 8.0
        if item.category != "عمومی":
            value += 3.0
        if item.provider == "Google News":
            value += 1.0
        return value

    return sorted(items, key=score, reverse=True)


def _sample_items(location: Location) -> list[NewsItem]:
    """داده ذخیرهشده برای مواقعی که وب در دسترس نیست."""
    target = location.target
    now = datetime.now(timezone.utc)
    templates = (
        ("ترافیک", f"ترافیک سنگین و کاهش سرعت در مسیر {target} در ساعات اوج رفت و آمد"),
        ("بسته شدن", f"انسداد موقت بخشی از {target} به دلیل عملیات راهداری"),
        ("شرایط نامناسب", f"لغزندگی سطح {target} به دلیل بارش و رطوبت هوا"),
    )
    return [
        NewsItem(
            title=title,
            url="",
            source="داده ذخیرهشده RoadRadar",
            published=now - timedelta(hours=3 + index * 5),
            snippet="این یک نمونه وضعیت است و بهصورت زنده از وب دریافت نشده است.",
            category=category,
            provider="Fallback",
        )
        for index, (category, title) in enumerate(templates)
    ]


async def search(location: Location) -> SearchResponse:
    """هیچوقت خطا نمیدهد؛ هوا را حتماً میآورد، اخبار هم اگر بود اضافه میکند."""
    queries: list[str] = []
    weather: WeatherInfo | None = None
    collected: list[NewsItem] = []
    ranked: list[NewsItem] = []

    # ----- مرحله ۱: اخبار + هوا (هر خطایی happen شود ignore میشود) -----
    try:
        queries = build_queries(location)
        coords = _coords_for(location)
        date_text = getattr(location, "date_text", None)
        client = httpx.AsyncClient(
            timeout=settings.search_timeout, headers=_HEADERS, follow_redirects=True
        )
        try:
            requests = []
            for query in queries:
                requests.append(_fetch_google(client, query))
                requests.append(_fetch_bing(client, query))
            weather_task = _fetch_weather(client, coords, date_text) if coords else None
            if weather_task is not None:
                requests.append(weather_task)
            raw_results = await asyncio.gather(*requests, return_exceptions=True)
        finally:
            await client.aclose()

        if weather_task is not None and raw_results:
            candidate = raw_results[-1]
            if isinstance(candidate, WeatherInfo):
                weather = candidate

        for result in raw_results:
            if isinstance(result, BaseException):
                log.debug("Search provider failed: %s", result)
                continue
            if isinstance(result, WeatherInfo):
                continue
            collected.extend(result)
    except Exception as exc:
        log.debug("News stage failed: %s", exc)

    # ----- مرحله ۲: اگر هوا نیامد، جداگانه و با retry دوباره بگیر -----
    if weather is None:
        weather = await weather_only(location)

    # ----- مرحله ۳: مرتبسازی اخبار (خطا نباید پیام را خراب کند) -----
    try:
        relevant = [
            item
            for item in _dedupe(collected)
            if _is_relevant(item, location) and not _is_accident(item)
        ]
        ranked = _rank(relevant, location)
    except Exception as exc:
        log.debug("Ranking stage failed: %s", exc)

    used_fallback = not ranked
    if used_fallback:
        try:
            ranked = _sample_items(location)
        except Exception:
            ranked = []

    return SearchResponse(
        items=ranked[: settings.max_results],
        queries=queries,
        used_fallback=used_fallback,
        total_found=len(ranked),
        weather=weather,
    )
