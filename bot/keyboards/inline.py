"""کیبوردهای شیشهای و callback dataها."""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..data.roads import get_city, get_province


class MenuCD(CallbackData, prefix="m"):
    action: str


class ProvinceCD(CallbackData, prefix="p"):
    id: str


class CityCD(CallbackData, prefix="c"):
    pid: str
    id: str


class RoadCD(CallbackData, prefix="r"):
    pid: str
    cid: str
    id: str


def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 بررسی وضعیت جاده", callback_data=MenuCD(action="status").pack())
    builder.button(text="✍️ جستجوی آزاد", callback_data=MenuCD(action="free").pack())
    builder.button(text="ℹ️ راهنما", callback_data=MenuCD(action="help").pack())
    builder.adjust(1)
    return builder.as_markup()


def provinces_kb() -> InlineKeyboardMarkup:
    from ..data.roads import PROVINCES

    builder = InlineKeyboardBuilder()
    for province in PROVINCES:
        builder.button(
            text=f"📍 {province.name}",
            callback_data=ProvinceCD(id=province.id).pack(),
        )
    builder.adjust(2)
    builder.button(text="🏠 منو", callback_data=MenuCD(action="home").pack())
    builder.adjust(1)
    return builder.as_markup()


def cities_kb(pid: str) -> InlineKeyboardMarkup:
    province = get_province(pid)
    builder = InlineKeyboardBuilder()
    if province:
        for city in province.cities:
            builder.button(
                text=f"🏙️ {city.name}",
                callback_data=CityCD(pid=pid, id=city.id).pack(),
            )
    builder.adjust(2)
    builder.button(text="🔙 استانها", callback_data=MenuCD(action="home_status").pack())
    builder.button(text="🏠 منو", callback_data=MenuCD(action="home").pack())
    builder.adjust(1)
    return builder.as_markup()


def roads_kb(pid: str, cid: str) -> InlineKeyboardMarkup:
    city = get_city(pid, cid)
    builder = InlineKeyboardBuilder()
    if city:
        for road in city.roads:
            builder.button(
                text=f"🛣️ {road.name}",
                callback_data=RoadCD(pid=pid, cid=cid, id=road.id).pack(),
            )
    builder.button(
        text="✍️ نام دیگهای وارد کن",
        callback_data=MenuCD(action="custom_road").pack(),
    )
    builder.adjust(1)
    builder.button(
        text="🔙 شهرها",
        callback_data=MenuCD(action="back_cities").pack(),
    )
    builder.button(text="🏠 منو", callback_data=MenuCD(action="home").pack())
    builder.adjust(1)
    return builder.as_markup()


def results_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 بروزرسانی همین مسیر", callback_data=MenuCD(action="refresh").pack())
    builder.button(text="🔍 جستجوی آزاد", callback_data=MenuCD(action="free").pack())
    builder.button(text="🔎 بررسی شهر دیگر", callback_data=MenuCD(action="status").pack())
    builder.button(text="🏠 منو", callback_data=MenuCD(action="home").pack())
    builder.adjust(1)
    return builder.as_markup()
