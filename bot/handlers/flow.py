"""جریان گامبهگام انتخاب استان/شهر/جاده و پردازش متن آزاد."""

from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..data import (
    PROVINCES,
    City,
    Location,
    Province,
    Road,
    find_city,
    find_province,
    find_road,
    get_city,
    get_province,
    get_road,
    parse_location,
)
from ..keyboards import (
    CityCD,
    MenuCD,
    ProvinceCD,
    RoadCD,
    cities_kb,
    main_menu,
    provinces_kb,
    roads_kb,
)
from ..services import format_help
from .commands import WELCOME
from .searcher import dict_to_location, location_to_dict, send_report
from .states import RoadStates

router = Router()

_DATE_WORDS = (
    "امروز", "فردا", "پسفردا", "پس فردا", "شنبه", "یکشنبه", "یک شنبه",
    "دوشنبه", "سهشنبه", "سه شنبه", "چهارشنبه", "چهار شنبه",
    "پنجشنبه", "پنج شنبه", "جمعه",
)


def _looks_like_date(text: str) -> bool:
    value = (text or "").strip()
    if any(word in value for word in _DATE_WORDS):
        return True
    return "/" in value and bool(re.search(r"\d", value))


def _owner_of_city(city: City) -> Province | None:
    return next((p for p in PROVINCES if any(c.id == city.id for c in p.cities)), None)


def _owner_of_road(road: Road) -> tuple[Province | None, City | None]:
    for province in PROVINCES:
        for city in province.cities:
            if any(r.id == road.id for r in city.roads):
                return province, city
    return None, None


def _context(data: dict) -> Province | None:
    return get_province(data.get("province_id"))


def _extract(text: str, data: dict):
    current = _context(data)
    pname = current.name if current else None
    province = find_province(text)
    city = find_city(text, pname) if pname else find_city(text)
    road = find_road(text, pname, city.name if city else None) if pname else find_road(text)
    if road is None and pname:
        road = find_road(text, pname)
    return province, city, road, current


# ---------- دکمههای منو ----------


@router.callback_query(MenuCD.filter(F.action.in_(["status", "home_status"])))
async def cb_status(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(RoadStates.province)
    await state.update_data(province_id=None, city_id=None, road_id=None)
    await call.message.edit_text("📍 استان مورد نظر را انتخاب کنید:", reply_markup=provinces_kb())
    await call.answer()


@router.callback_query(MenuCD.filter(F.action == "home"))
async def cb_home(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(WELCOME, reply_markup=main_menu())
    await call.answer()


@router.callback_query(MenuCD.filter(F.action == "help"))
async def cb_help(call: CallbackQuery) -> None:
    await call.message.edit_text(format_help(), reply_markup=main_menu())
    await call.answer()


@router.callback_query(MenuCD.filter(F.action == "free"))
async def cb_free(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(RoadStates.free_query)
    await call.message.edit_text(
        "✍️ عبارت جستجو را بنویسید، مثلاً:\n"
        "«مازندران / چالوس / جاده چالوس»\n"
        "یا «ترافیک جاده هراز امروز»",
        reply_markup=main_menu(),
    )
    await call.answer()


@router.callback_query(MenuCD.filter(F.action == "custom_road"))
async def cb_custom_road(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(RoadStates.custom_road)
    await call.message.edit_text("✍️ نام جاده یا خیابان را بنویسید:")
    await call.answer()


@router.callback_query(MenuCD.filter(F.action == "back_cities"))
async def cb_back_cities(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    pid = data.get("province_id")
    province = get_province(pid)
    if not province:
        await cb_status(call, state)
        return
    await state.set_state(RoadStates.city)
    await call.message.edit_text(
        f"📍 {province.name}\n🏙️ شهر را انتخاب کنید:",
        reply_markup=cities_kb(province.id),
    )
    await call.answer()


@router.callback_query(MenuCD.filter(F.action == "refresh"))
async def cb_refresh(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    location = dict_to_location(data.get("last_location"))
    if not location:
        await cb_status(call, state)
        return
    await call.answer()
    await send_report(call.message, location, state)


# ---------- انتخاب گامبهگام ----------


@router.callback_query(ProvinceCD.filter())
async def cb_province(
    call: CallbackQuery, callback_data: ProvinceCD, state: FSMContext
) -> None:
    province = get_province(callback_data.id)
    if not province:
        await call.answer("استان ناشناخته است", show_alert=True)
        return
    await state.set_state(RoadStates.city)
    await state.update_data(province_id=province.id, city_id=None, road_id=None)
    await call.message.edit_text(
        f"📍 {province.name}\n🏙️ شهر را انتخاب کنید:",
        reply_markup=cities_kb(province.id),
    )
    await call.answer()


@router.callback_query(CityCD.filter())
async def cb_city(call: CallbackQuery, callback_data: CityCD, state: FSMContext) -> None:
    province = get_province(callback_data.pid)
    city = get_city(callback_data.pid, callback_data.id)
    if not province or not city:
        await call.answer("شهر ناشناخته است", show_alert=True)
        return
    await state.set_state(RoadStates.road)
    await state.update_data(province_id=province.id, city_id=city.id, road_id=None)
    await call.message.edit_text(
        f"📍 {province.name} / {city.name}\n🛣️ جاده یا خیابان را انتخاب کنید:",
        reply_markup=roads_kb(province.id, city.id),
    )
    await call.answer()


@router.callback_query(RoadCD.filter())
async def cb_road(call: CallbackQuery, callback_data: RoadCD, state: FSMContext) -> None:
    province = get_province(callback_data.pid)
    city = get_city(callback_data.pid, callback_data.cid)
    road = get_road(callback_data.pid, callback_data.cid, callback_data.id)
    if not province or not city or not road:
        await call.answer("مسیر ناشناخته است", show_alert=True)
        return
    await state.update_data(road_id=road.id)
    await call.answer()
    location = Location(province=province.name, city=city.name, road=road.name)
    await state.update_data(pending_location=location_to_dict(location))
    await state.set_state("date")
    await call.message.edit_text(
        "🗓️ برای چه تاریخی وضعیت را بیاورم؟\n\n"
        "مثلاً بنویس:\n"
        "• امروز / فردا / پسفردا\n"
        "• دوشنبه / سهشنبه / جمعه\n"
        "• یا تاریخ مشخص مثل ۱۴۰۵/۰۹/۲۵",
        reply_markup=main_menu(),
    )


# ---------- متن آزاد ----------


@router.message()
async def handle_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        return

    current = await state.get_state()
    data = await state.get_data()

    if current == RoadStates.done.state and _looks_like_date(text):
        last_location = dict_to_location(data.get("last_location"))
        if last_location is not None:
            last_location.date_text = text
            await send_report(message, last_location, state)
            return

    if current == "date":
        pending = dict_to_location(data.get("pending_location"))
        if pending is None:
            await state.set_state(RoadStates.province)
            await message.answer("📍 استان را انتخاب کنید:", reply_markup=provinces_kb())
            return
        pending.date_text = text
        await state.set_state(RoadStates.done)
        await send_report(message, pending, state)
        return

    province, city, road, current_province = _extract(text, data)

    if current == RoadStates.province.state:
        chosen = province
        if chosen is None and city is not None:
            chosen = _owner_of_city(city)
        if chosen is None and road is not None:
            chosen = _owner_of_road(road)[0]
        if chosen:
            await state.update_data(province_id=chosen.id, city_id=None, road_id=None)
            await state.set_state(RoadStates.city)
            await message.answer(
                f"📍 {chosen.name}\n🏙️ شهر را انتخاب کنید:",
                reply_markup=cities_kb(chosen.id),
            )
        else:
            await state.set_state(RoadStates.done)
            await send_report(message, parse_location(text), state)
        return

    if current == RoadStates.city.state:
        if province and (current_province is None or province.id != current_province.id):
            await state.update_data(province_id=province.id, city_id=None, road_id=None)
            await state.set_state(RoadStates.city)
            await message.answer(
                f"📍 {province.name}\n🏙️ شهر را انتخاب کنید:",
                reply_markup=cities_kb(province.id),
            )
        elif city:
            await state.update_data(city_id=city.id, road_id=None)
            await state.set_state(RoadStates.road)
            await message.answer(
                f"📍 {current_province.name if current_province else ''} / {city.name}\n"
                "🛣️ جاده یا خیابان را انتخاب کنید:",
                reply_markup=roads_kb(current_province.id, city.id) if current_province else main_menu(),
            )
        elif road:
            owner_province, owner_city = _owner_of_road(road)
            if owner_province:
                await state.update_data(province_id=owner_province.id, city_id=owner_city.id if owner_city else None)
                await state.set_state(RoadStates.road)
                await message.answer(
                    f"🛣️ {road.name}\nمسیر دیگری هم هست یا همین را بررسی کنم؟",
                    reply_markup=roads_kb(owner_province.id, owner_city.id) if owner_city else main_menu(),
                )
            else:
                await state.set_state(RoadStates.done)
                await send_report(message, Location(free_query=text), state)
        else:
            location = Location(
                province=current_province.name if current_province else None,
                free_query=text,
            )
            await state.set_state(RoadStates.done)
            await send_report(message, location, state)
        return

    if current == RoadStates.road.state:
        if road:
            owner_province, owner_city = _owner_of_road(road)
            location = Location(
                province=(owner_province or current_province).name if (owner_province or current_province) else None,
                city=owner_city.name if owner_city else (get_city(data.get("province_id"), data.get("city_id")).name if get_city(data.get("province_id"), data.get("city_id")) else None),
                road=road.name,
            )
            await state.set_state(RoadStates.done)
            await send_report(message, location, state)
        elif city:
            pid = current_province.id if current_province else None
            await state.update_data(city_id=city.id, road_id=None)
            await state.set_state(RoadStates.road)
            await message.answer(
                f"🏙️ {city.name}\n🛣️ جاده یا خیابان را انتخاب کنید:",
                reply_markup=roads_kb(pid, city.id) if pid else main_menu(),
            )
        elif province:
            await state.update_data(province_id=province.id, city_id=None, road_id=None)
            await state.set_state(RoadStates.city)
            await message.answer(
                f"📍 {province.name}\n🏙️ شهر را انتخاب کنید:",
                reply_markup=cities_kb(province.id),
            )
        else:
            city_obj = get_city(data.get("province_id"), data.get("city_id"))
            location = Location(
                province=current_province.name if current_province else None,
                city=city_obj.name if city_obj else None,
                road=text,
            )
            await state.set_state(RoadStates.done)
            await send_report(message, location, state)
        return

    if current == RoadStates.custom_road.state:
        city_obj = get_city(data.get("province_id"), data.get("city_id"))
        location = Location(
            province=current_province.name if current_province else None,
            city=city_obj.name if city_obj else None,
            road=text,
        )
        await state.set_state(RoadStates.done)
        await send_report(message, location, state)
        return

    # حالت آزاد (بدون حالت یا بعد از دریافت نتیجه)
    await state.set_state(RoadStates.done)
    await send_report(message, parse_location(text), state)
