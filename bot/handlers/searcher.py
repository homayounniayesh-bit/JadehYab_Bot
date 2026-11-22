"""منطق مشترک ارسال نتیجه جستجو."""

from __future__ import annotations

import logging

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..data.roads import Location
from ..keyboards import results_kb
from ..services import format_results, search

log = logging.getLogger(__name__)


def location_to_dict(location: Location) -> dict:
    return {
        "province": location.province,
        "city": location.city,
        "road": location.road,
        "free_query": location.free_query,
    }


def dict_to_location(data: dict | None) -> Location | None:
    if not data:
        return None
    return Location(
        province=data.get("province"),
        city=data.get("city"),
        road=data.get("road"),
        free_query=data.get("free_query"),
    )


async def send_report(message: Message, location: Location, state: FSMContext | None = None) -> None:
    if state is not None:
        await state.update_data(last_location=location_to_dict(location))
    pending = await message.answer("🔎 در حال جستجوی وضعیت جاده ...")
    try:
        response = await search(location)
        await message.answer(
            format_results(location, response),
            reply_markup=results_kb(),
        )
    except Exception:
        log.exception("Failed to build/send road report")
        await message.answer(
            "❌ خطایی در جستجو رخ داد. لطفاً کمی بعد دوباره تلاش کنید.",
            reply_markup=results_kb(),
        )
    finally:
        try:
            await pending.delete()
        except Exception:
            pass
