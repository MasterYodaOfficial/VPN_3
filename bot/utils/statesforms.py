from aiogram.fsm.state import StatesGroup, State


class StepForm(StatesGroup):
    """
    Машина состояний передвижения в меню
    """

    # Profile движения
    COMMAND = State()

