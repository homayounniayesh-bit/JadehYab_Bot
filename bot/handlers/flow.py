"""جریان ساده: استان → شهر → وضعیت الان (بدون جاده و تاریخ)."""

from __future__ import annotations

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
)
from ..services import format_help
from .commands import WELCOME
from .searcher import dict_to_location, send_report
from .states import RoadStates

router = Router()


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


def _city_location(city: City, province: Province | None = None) -> Location:
    owner = _owner_of_city(city)
    if province and owner and province.id != owner.id:
        province = owner
    province = province or owner
    return Location(province=province.name if province else None, city=city.name)


def _complete(location: Location, data: dict | None = None) -> Location:
    """هر ورودی رو به یک شهر تبدیل میکند؛ جاده و تاریخ حذف میشوند."""
    data = data or {}
    province = get_province(data.get("province_id"))
    if location.province and province is None:
        province = find_province(location.province)

    city = find_city(location.city) if location.city else None

    if city is None and location.road:
        road = find_road(location.road)
        if road:
            owner_province, owner_city = _owner_of_road(road)
            city = owner_city
            province = province or owner_province

    if city is None and location.free_query:
        city = find_city(
            location.free_query, province.name if province else None
        ) or find_city(location.free_query)
        if city is None:
            road = find_road(location.free_query)
            if road:
                owner_province, owner_city = _owner_of_road(road)
                city = owner_city
                province = province or owner_province
        if city is None:
            for token in location.free_query.replace("/", " ").split():
                if len(token) < 3:
                    continue
                city = find_city(token, province.name if province else None) or find_city(token)
                if city:
                    break
                found_province = find_province(token)
                if found_province:
                    province = province or found_province

    if city:
        return _city_location(city, province)

    if get_city(data.get("province_id"), data.get("city_id")):
        return _city_location(get_city(data.get("province_id"), data.get("city_id")), province)

    if province:
        return Location(province=province.name)

    return Location(free_query=location.free_query or location.road or "جاده")


async def _show_cities(
    target, province: Province, state: FSMContext, *, edit: bool = False
) -> None:
    await state.set_state(RoadStates.city)
    await state.update_data(province_id=province.id, city_id=None)
    text = f"📍 {province.name}\n🏙️ شهر را انتخاب کنید:"
    markup = cities_kb(province.id)
    if edit:
        await target.edit_text(text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)


# ---------- دکمههای منو ----------


@router.callback_query(MenuCD.filter(F.action.in_(["status", "home_status"])))
async def cb_status(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(RoadStates.province)
    await state.update_data(province_id=None, city_id=None)
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
        "✍️ نام شهر را بنویسید، مثلاً:\n"
        "«چالوس» یا «مشهد» یا «ترافیک اصفهان»",
        reply_markup=main_menu(),
    )
    await call.answer()


@router.callback_query(MenuCD.filter(F.action == "custom_road"))
async def cb_custom_road(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(RoadStates.free_query)
    await call.message.edit_text("✍️ نام شهر را بنویسید:")
    await call.answer()


@router.callback_query(MenuCD.filter(F.action == "back_cities"))
async def cb_back_cities(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    province = get_province(data.get("province_id"))
    if not province:
        await cb_status(call, state)
        return
    await _show_cities(call.message, province, state, edit=True)
    await call.answer()


@router.callback_query(MenuCD.filter(F.action == "refresh"))
async def cb_refresh(call: CallbackQuery, state: FSMContext) -> None:
    location = dict_to_location((await state.get_data()).get("last_location"))
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
    await call.answer()
    await _show_cities(call.message, province, state, edit=True)


@router.callback_query(CityCD.filter())
async def cb_city(call: CallbackQuery, callback_data: CityCD, state: FSMContext) -> None:
    province = get_province(callback_data.pid)
    city = get_city(callback_data.pid, callback_data.id)
    if not province or not city:
        await call.answer("شهر ناشناخته است", show_alert=True)
        return
    await call.answer()
    location = _city_location(city, province)
    await state.set_state(RoadStates.done)
    await send_report(call.message, location, state)


@router.callback_query(RoadCD.filter())
async def cb_road(call: CallbackQuery, callback_data: RoadCD, state: FSMContext) -> None:
    """دکمه قدیمی جاده هم حالا فقط وضعیت همان شهر رو میدهد."""
    city = get_city(callback_data.pid, callback_data.cid)
    if not city:
        await call.answer("شهر ناشناخته است", show_alert=True)
        return
    await call.answer()
    location = _city_location(city, get_province(callback_data.pid))
    await state.set_state(RoadStates.done)
    await send_report(call.message, location, state)


# ---------- متن آزاد ----------


@router.message()
async def handle_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        return

    data = await state.get_data()
    current_province = _context(data)

    province = find_province(text)
    scope = province.name if province else (current_province.name if current_province else None)
    city = find_city(text, scope) or find_city(text)
    road = find_road(text, scope) or find_road(text)

    # فقط استان نوشت → لیست شهرها
    if province and city is None and road is None:
        await _show_cities(message, province, state)
        return

    # اگر نام جادهای نوشت، صاحب آن شهر را پیدا کن
    if city is None and road:
        owner_province, owner_city = _owner_of_road(road)
        city = owner_city
        province = province or owner_province

    if city:
        location = _city_location(city, province or current_province)
    else:
        location = _complete(parse_location(text, data), data)
        if location.province and location.city is None:
            only_province = find_province(location.province)
            if only_province:
                await _show_cities(message, only_province, state)
                return

    await state.set_state(RoadStates.done)
    await send_report(message, location, state)
