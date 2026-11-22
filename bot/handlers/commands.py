"""دستورات اصلی بات."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..data import parse_location
from ..keyboards import main_menu, provinces_kb
from ..services import format_help
from .searcher import send_report
from .states import RoadStates

router = Router()

WELCOME = (
    "👋 سلام! به <b>RoadRadar</b> خوش آمدید.\n\n"
    "🛣️ من وضعیت جادهها را در شهرهای سراسر ایران پیدا میکنم:\n"
    "🚗 ترافیک · 🚧 بستهشدن · ⛈️ شرایط نامناسب\n\n"
    "فقط استان و شهر را انتخاب کنید (یا بنویسید) تا وضعیت الان را "
    "برایتان بگویم.\n\n"
    "برای شروع دکمه زیر را بزنید 👇"
)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME, reply_markup=main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(format_help(), reply_markup=main_menu())


@router.message(Command("status"))
async def cmd_status(message: Message, state: FSMContext) -> None:
    await state.set_state(RoadStates.province)
    await message.answer("📍 استان مورد نظر را انتخاب کنید:", reply_markup=provinces_kb())


@router.message(Command("search"))
async def cmd_search(message: Message, command: CommandObject, state: FSMContext) -> None:
    args = (command.args or "").strip()
    if not args:
        await message.answer(
            "✍️ بعد از دستور، نام شهر را هم بنویسید، مثل:\n"
            "<code>/search چالوس</code>"
        )
        return
    await state.set_state(RoadStates.done)
    await send_report(message, parse_location(args), state)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("✅ عملیات فعلی لغو شد.", reply_markup=main_menu())
