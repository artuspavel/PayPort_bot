"""FSM States for the bot."""
from aiogram.fsm.state import State, StatesGroup


class QuestionnaireStates(StatesGroup):
    """States for questionnaire filling."""
    answering = State()  # User is answering questions
    waiting_passport_photo = State()  # Waiting for passport photo
    waiting_passport_selfie = State()  # Waiting for selfie video with passport


class AdminStates(StatesGroup):
    """States for admin operations."""
    adding_operator = State()  # Admin is adding operator
    editing_question = State()  # Admin is editing question
    adding_question = State()  # Admin is adding new question


class OperatorStates(StatesGroup):
    """States for operator operations."""
    creating_invite = State()  # Operator is creating invite with description

