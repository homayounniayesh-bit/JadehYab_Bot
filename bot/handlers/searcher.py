"""منطق مشترک ارسال نتیجه — هیچوقت پیام خطا نمیدهد، هوا همیشه ارسال میشود."""

from __future__ import annotations

import logging

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..data.roads import Location
from ..keyboards import results_kb
from ..services import SearchResponse, format_results, search, weather_only

log = logging.getLogger(__name__)


def location_to_dict(location: Location) -> dict:
    return {
        "province": location.province,
        "city": location.city,
        "road": location.road,
        "free_query": location.free_query,
        "date_text": location.date_text,
    }


def dict_to_location(data: dict | None) -> Location | None:
    if not data:
        return None
    return Location(
        province=data.get("province"),
        city=data.get("city"),
        road=data.get("road"),
        free_query=data.get("free_query"),
        date_text=data.get("date_text"),
    )


async def send_report(
    message: Message, location: Location, state: FSMContext | None = None
) -> None:
    if state is not None:
        try:
            await state.update_data(last_location=location_to_dict(location))
        except Exception:
            pass

    try:
        pending = await message.answer("🔎 در حال جستجوی وضعیت جاده ...")
    except Exception:
        pending = None

    # جستجو göre خودش ایمن است؛ ولی باز هم guard میگذاریم تا خطا به کاربر نرسد
    try:
        response = await search(location)
    except Exception:
        log.exception("search() failed unexpectedly")
        response = None

    # اگر هوا نیامد، جداگانه با retry بگیر — پیام خطا به کاربر نشان نده
    if response is None or response.weather is None:
        try:
            weather = await weather_only(location)
        except Exception:
            log.debug("weather_only failed", exc_info=True)
            weather = None
        if response is None:
            response = SearchResponse(
                items=[],
                queries=[],
                used_fallback=True,
                total_found=0,
                weather=weather,
            )
        else:
            response.weather = weather

    try:
        text = format_results(location, response)
    except Exception:
        log.exception("format_results failed unexpectedly")
        text = "🌤️ <b>آب و هوا</b>\n  ⏳ در حال بروزرسانی اطلاعات هوا..."

    try:
        await message.answer(text, reply_markup=results_kb())
    except Exception:
        log.exception("Failed to send report message")

    try:
        if pending is not None:
            await pending.delete()
    except Exception:
        pass
