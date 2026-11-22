from aiogram.fsm.state import State, StatesGroup


class RoadStates(StatesGroup):
    province = State()
    city = State()
    road = State()
    custom_road = State()
    free_query = State()
    date = State()
    done = State()
