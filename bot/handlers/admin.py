"""Admin handlers."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot import database as db
from bot.states import AdminStates
from bot.keyboards import (
    admin_menu, cancel_button, questions_list_keyboard,
    operators_list_keyboard, confirm_keyboard, questions_menu_keyboard
)

router = Router()


# ============ Middleware-like check ============

async def is_admin(user_telegram_id: int) -> bool:
    """Check if user is admin."""
    user = await db.get_user_by_telegram_id(user_telegram_id)
    return user and user['is_admin']


# ============ Menu Callbacks ============

@router.callback_query(F.data == "admin:menu")
async def admin_menu_callback(callback: CallbackQuery, state: FSMContext):
    """Show admin menu."""
    await state.clear()
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "👑 Меню администратора:",
        reply_markup=admin_menu()
    )
    await callback.answer()


# ============ Add Operator ============

@router.callback_query(F.data == "admin:add_operator")
async def add_operator_start(callback: CallbackQuery, state: FSMContext):
    """Start adding operator."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.set_state(AdminStates.adding_operator)
    await callback.message.edit_text(
        "👤 Введите username нового оператора (с @ или без):",
        reply_markup=cancel_button()
    )
    await callback.answer()


@router.message(AdminStates.adding_operator)
async def add_operator_process(message: Message, state: FSMContext):
    """Process adding operator."""
    if not await is_admin(message.from_user.id):
        await state.clear()
        return
    
    username = message.text.strip().lstrip('@')
    
    if not username or len(username) < 3:
        await message.answer(
            "❌ Некорректный username. Попробуйте ещё раз:",
            reply_markup=cancel_button()
        )
        return
    
    success = await db.add_operator(username, message.from_user.id)
    
    if success:
        await message.answer(
            f"✅ Оператор @{username} успешно добавлен!\n\n"
            "Теперь этот пользователь может использовать бота.",
            reply_markup=admin_menu()
        )
    else:
        await message.answer(
            f"⚠️ Оператор @{username} уже существует.",
            reply_markup=admin_menu()
        )
    
    await state.clear()


# ============ Remove Operator ============

@router.callback_query(F.data == "admin:remove_operator")
async def remove_operator_start(callback: CallbackQuery, state: FSMContext):
    """Show operators list for removal."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    operators = await db.list_operators()
    # Filter out admins
    operators = [op for op in operators if not op['is_admin']]
    
    if not operators:
        await callback.message.edit_text(
            "📭 Нет операторов для удаления.",
            reply_markup=admin_menu()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "👥 Выберите оператора для удаления:",
        reply_markup=operators_list_keyboard(operators, "remove")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("remove_op:"))
async def remove_operator_confirm(callback: CallbackQuery, state: FSMContext):
    """Confirm operator removal."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    username = callback.data.split(":")[1]
    await state.update_data(remove_username=username)
    
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить оператора @{username}?",
        reply_markup=confirm_keyboard("remove_operator")
    )
    await callback.answer()


@router.callback_query(F.data == "confirm:remove_operator")
async def remove_operator_execute(callback: CallbackQuery, state: FSMContext):
    """Execute operator removal."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    data = await state.get_data()
    username = data.get('remove_username')
    
    if username:
        success = await db.remove_operator(username)
        if success:
            await callback.message.edit_text(
                f"✅ Оператор @{username} удалён.",
                reply_markup=admin_menu()
            )
        else:
            await callback.message.edit_text(
                f"❌ Не удалось удалить оператора @{username}.",
                reply_markup=admin_menu()
            )
    
    await state.clear()
    await callback.answer()


# ============ List Operators ============

@router.callback_query(F.data == "admin:list_operators")
async def list_operators(callback: CallbackQuery):
    """Show operators list."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    operators = await db.list_operators()
    
    if not operators:
        text = "📭 Список операторов пуст."
    else:
        # NOTE: Using HTML to avoid Markdown issues with underscores in usernames
        text = "<b>👥 Список пользователей:</b>\n\n"
        for op in operators:
            status = "👑 Админ" if op['is_admin'] else "👤 Оператор"
            tg_status = "✅" if op['telegram_id'] else "⏳"
            text += f"{tg_status} {status}: @{op['username']}\n"
        
        text += "\n✅ - авторизован в боте\n⏳ - ещё не заходил в бот"
    
    await callback.message.edit_text(
        text,
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )
    await callback.answer()


# ============ Make Admin ============

@router.callback_query(F.data == "admin:make_admin")
async def make_admin_start(callback: CallbackQuery, state: FSMContext):
    """Show operators list to promote to admin."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    operators = await db.list_operators()
    # Filter only non-admins
    operators = [op for op in operators if not op['is_admin']]
    
    if not operators:
        await callback.message.edit_text(
            "📭 Нет операторов для назначения админом.\n"
            "Сначала добавьте операторов.",
            reply_markup=admin_menu()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "👑 Выберите оператора для назначения админом:",
        reply_markup=operators_list_keyboard(operators, "promote")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("promote_op:"))
async def make_admin_confirm(callback: CallbackQuery, state: FSMContext):
    """Confirm promoting to admin."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    username = callback.data.split(":")[1]
    await state.update_data(promote_username=username)
    
    await callback.message.edit_text(
        f"👑 Назначить @{username} администратором?\n\n"
        "⚠️ Админ получит полный доступ к управлению ботом.",
        reply_markup=confirm_keyboard("make_admin")
    )
    await callback.answer()


@router.callback_query(F.data == "confirm:make_admin")
async def make_admin_execute(callback: CallbackQuery, state: FSMContext):
    """Execute admin promotion."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    data = await state.get_data()
    username = data.get('promote_username')
    
    if username:
        success = await db.make_admin(username)
        if success:
            await callback.message.edit_text(
                f"✅ @{username} теперь администратор!",
                reply_markup=admin_menu()
            )
        else:
            await callback.message.edit_text(
                f"❌ Не удалось назначить @{username} админом.",
                reply_markup=admin_menu()
            )
    
    await state.clear()
    await callback.answer()


# ============ Questions Management Menu ============

@router.callback_query(F.data == "admin:edit_questions")
async def questions_menu(callback: CallbackQuery):
    """Show questions management menu."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    questions = await db.get_all_questions()
    
    await callback.message.edit_text(
        f"📝 **Управление вопросами**\n\n"
        f"Всего вопросов: {len(questions)}\n\n"
        "Выберите действие:",
        reply_markup=questions_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


# ============ Edit Questions ============

@router.callback_query(F.data == "questions:edit_list")
async def edit_questions_list(callback: CallbackQuery):
    """Show questions list for editing."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    questions = await db.get_all_questions()
    
    if not questions:
        await callback.message.edit_text(
            "📭 Вопросы не найдены.",
            reply_markup=questions_menu_keyboard()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"✏️ **Редактирование вопросов ({len(questions)}):**\n\n"
        "Выберите вопрос для редактирования:",
        reply_markup=questions_list_keyboard(questions, "edit"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_q:"))
async def edit_question_start(callback: CallbackQuery, state: FSMContext):
    """Start editing specific question."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    question_id = int(callback.data.split(":")[1])
    questions = await db.get_all_questions()
    question = next((q for q in questions if q['id'] == question_id), None)
    
    if not question:
        await callback.answer("❌ Вопрос не найден", show_alert=True)
        return
    
    await state.set_state(AdminStates.editing_question)
    await state.update_data(editing_question_id=question_id)
    
    await callback.message.edit_text(
        f"✏️ **Редактирование вопроса:**\n\n"
        f"Текущий текст:\n`{question['text']}`\n\n"
        "Введите новый текст вопроса:",
        reply_markup=cancel_button(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(AdminStates.editing_question)
async def edit_question_process(message: Message, state: FSMContext):
    """Process question editing."""
    if not await is_admin(message.from_user.id):
        await state.clear()
        return
    
    data = await state.get_data()
    question_id = data.get('editing_question_id')
    
    new_text = message.text.strip()
    
    if not new_text:
        await message.answer(
            "❌ Текст вопроса не может быть пустым.",
            reply_markup=cancel_button()
        )
        return
    
    success = await db.update_question(question_id, new_text)
    
    if success:
        await message.answer(
            "✅ Вопрос успешно обновлён!",
            reply_markup=questions_menu_keyboard()
        )
    else:
        await message.answer(
            "❌ Ошибка при обновлении вопроса.",
            reply_markup=questions_menu_keyboard()
        )
    
    await state.clear()


# ============ Add Question ============

@router.callback_query(F.data == "questions:add")
async def add_question_start(callback: CallbackQuery, state: FSMContext):
    """Start adding new question."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.set_state(AdminStates.adding_question)
    await callback.message.edit_text(
        "➕ **Добавление нового вопроса**\n\n"
        "Введите текст нового вопроса:\n"
        "(например: `33) Your question text here:`)",
        reply_markup=cancel_button(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(AdminStates.adding_question)
async def add_question_process(message: Message, state: FSMContext):
    """Process adding new question."""
    if not await is_admin(message.from_user.id):
        await state.clear()
        return
    
    new_text = message.text.strip()
    
    if not new_text:
        await message.answer(
            "❌ Текст вопроса не может быть пустым.",
            reply_markup=cancel_button()
        )
        return
    
    # Get current max order_num
    questions = await db.get_all_questions()
    max_order = max([q['order_num'] for q in questions]) if questions else 0
    new_order = max_order + 1
    
    # Generate unique key from text
    import re
    key_base = re.sub(r'[^a-z0-9]+', '_', new_text.lower()[:30]).strip('_')
    key = f"{key_base}_{new_order}"
    
    success = await db.add_question(new_order, new_text, key)
    
    if success:
        await message.answer(
            f"✅ Вопрос добавлен!\n\n"
            f"Позиция: #{new_order}\n"
            f"Текст: {new_text[:100]}{'...' if len(new_text) > 100 else ''}",
            reply_markup=questions_menu_keyboard()
        )
    else:
        await message.answer(
            "❌ Ошибка при добавлении вопроса.",
            reply_markup=questions_menu_keyboard()
        )
    
    await state.clear()


# ============ Delete Question ============

@router.callback_query(F.data == "questions:delete_list")
async def delete_questions_list(callback: CallbackQuery):
    """Show questions list for deletion."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    questions = await db.get_all_questions()
    
    if not questions:
        await callback.message.edit_text(
            "📭 Вопросы не найдены.",
            reply_markup=questions_menu_keyboard()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"🗑 **Удаление вопросов ({len(questions)}):**\n\n"
        "⚠️ Выберите вопрос для удаления:",
        reply_markup=questions_list_keyboard(questions, "delete"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_q:"))
async def delete_question_confirm(callback: CallbackQuery, state: FSMContext):
    """Confirm question deletion."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    question_id = int(callback.data.split(":")[1])
    questions = await db.get_all_questions()
    question = next((q for q in questions if q['id'] == question_id), None)
    
    if not question:
        await callback.answer("❌ Вопрос не найден", show_alert=True)
        return
    
    await state.update_data(delete_question_id=question_id)
    
    await callback.message.edit_text(
        f"⚠️ **Удалить этот вопрос?**\n\n"
        f"`{question['text']}`\n\n"
        "Это действие нельзя отменить!",
        reply_markup=confirm_keyboard("delete_question"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "confirm:delete_question")
async def delete_question_execute(callback: CallbackQuery, state: FSMContext):
    """Execute question deletion."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    data = await state.get_data()
    question_id = data.get('delete_question_id')
    
    if question_id:
        success = await db.delete_question(question_id)
        if success:
            await callback.message.edit_text(
                "✅ Вопрос удалён.",
                reply_markup=questions_menu_keyboard()
            )
        else:
            await callback.message.edit_text(
                "❌ Ошибка при удалении вопроса.",
                reply_markup=questions_menu_keyboard()
            )
    
    await state.clear()
    await callback.answer()

