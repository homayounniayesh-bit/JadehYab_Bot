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
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from ..config import settings
from ..data.roads import Location, find_road, norm

log = logging.getLogger(__name__)

CATEGORY_ORDER = ("ترافیک", "تصادف", "بسته شدن", "شرایط نامناسب", "عمومی")
CATEGORY_ICONS = {
    "ترافیک": "🚗",
    "تصادف": "🚨",
    "بسته شدن": "🚧",
    "شرایط نامناسب": "⛈️",
    "عمومی": "ℹ️",
}
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "بسته شدن": (
        "بسته", "مسدود", "انسداد", "قطع", "تجاوز از ظرفیت", "تعطیلی", "بسته شدن",
        "closed", "closure",
    ),
    "تصادف": (
        "تصادف", "سانحه", "حادثه", "برخورد", "واژگون", "مجروح", "کشته", "فوت",
        "کامیون", "اتوبوس", "خودرو", "crash", "accident",
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
    queries = [target, f"{target} ترافیک", f"{target} تصادف"]
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
    "جاده", "ترافیک", "راه", "مسیر", "رانندگی", "تصادف", "خودرو", "راهداری",
))


def _is_relevant(item: NewsItem, location: Location) -> bool:
    if location.free_query:
        return True
    text = norm(f"{item.title} {item.snippet}")
    for value in (location.target, location.city, location.province):
        if value and norm(value) in text:
            return True
    return any(term in text for term in _ROAD_TERMS)


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
        ("تصادف", f"سانحه رانندگی در {target} و ایجاد گره ترافیکی موقت"),
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
    queries = build_queries(location)
    client = httpx.AsyncClient(timeout=settings.search_timeout, headers=_HEADERS, follow_redirects=True)
    try:
        requests = []
        for query in queries:
            requests.append(_fetch_google(client, query))
            requests.append(_fetch_bing(client, query))
        raw_results = await asyncio.gather(*requests, return_exceptions=True)
    finally:
        await client.aclose()

    collected: list[NewsItem] = []
    for result in raw_results:
        if isinstance(result, BaseException):
            log.debug("Search provider failed: %s", result)
            continue
        collected.extend(result)

    relevant = [item for item in _dedupe(collected) if _is_relevant(item, location)]
    ranked = _rank(relevant, location)
    used_fallback = not ranked
    if used_fallback:
        ranked = _sample_items(location)

    return SearchResponse(
        items=ranked[: settings.max_results],
        queries=queries,
        used_fallback=used_fallback,
        total_found=len(ranked),
    )
