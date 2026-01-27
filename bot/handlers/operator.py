"""Operator handlers."""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from bot import database as db
from bot.states import OperatorStates
from bot.keyboards import (
    operator_menu, cancel_button, skip_description_keyboard, 
    language_selection_keyboard, invite_created_keyboard,
    invites_list_keyboard, invite_detail_keyboard, back_to_invite_keyboard,
    all_questionnaires_keyboard, operators_filter_keyboard
)
from bot.locales import LANGUAGES
from bot.document_generator import generate_questionnaire_docx

router = Router()


# ============ Helper ============

async def is_operator(user_telegram_id: int) -> bool:
    """Check if user is operator (or admin)."""
    user = await db.get_user_by_telegram_id(user_telegram_id)
    return user is not None


async def get_operator_id(user_telegram_id: int) -> int:
    """Get operator's database ID."""
    user = await db.get_user_by_telegram_id(user_telegram_id)
    return user['id'] if user else None


# ============ Create Invite ============

@router.callback_query(F.data == "operator:create_invite")
async def create_invite_start(callback: CallbackQuery, state: FSMContext):
    """Start creating invite - first select language."""
    if not await is_operator(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🌐 **Выберите язык анкеты:**\n\n"
        "На каком языке респондент будет видеть вопросы?",
        reply_markup=language_selection_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lang:"))
async def create_invite_language_selected(callback: CallbackQuery, state: FSMContext):
    """Language selected, now ask for description."""
    if not await is_operator(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    language = callback.data.split(":")[1]
    lang_name = LANGUAGES.get(language, language)
    
    await state.set_state(OperatorStates.creating_invite)
    await state.update_data(invite_language=language)
    
    await callback.message.edit_text(
        f"🔗 **Создание ссылки-приглашения**\n"
        f"🌐 Язык: {lang_name}\n\n"
        "Введите описание для этой ссылки (например, имя провайдера или компании).\n"
        "Это поможет вам отличать анкеты друг от друга.\n\n"
        "Или нажмите кнопку ниже, чтобы пропустить.",
        reply_markup=skip_description_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "skip_description", OperatorStates.creating_invite)
async def create_invite_skip_description(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Create invite without description."""
    data = await state.get_data()
    language = data.get('invite_language', 'en')
    await create_invite_execute(callback.message, state, bot, callback.from_user.id, None, language)
    await callback.answer()


@router.message(OperatorStates.creating_invite)
async def create_invite_with_description(message: Message, state: FSMContext, bot: Bot):
    """Create invite with description."""
    data = await state.get_data()
    language = data.get('invite_language', 'en')
    description = message.text.strip()
    await create_invite_execute(message, state, bot, message.from_user.id, description, language)


async def create_invite_execute(message: Message, state: FSMContext, bot: Bot, 
                                user_telegram_id: int, description: str, language: str):
    """Execute invite creation."""
    operator_id = await get_operator_id(user_telegram_id)
    
    if not operator_id:
        await message.answer("❌ Ошибка: оператор не найден.")
        await state.clear()
        return
    
    invite_code = await db.create_invite(operator_id, description, language)
    
    # Get bot username
    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start={invite_code}"
    
    lang_name = LANGUAGES.get(language, language)
    desc_text = f"\n📝 Описание: {description}" if description else ""
    
    await message.answer(
        f"✅ **Ссылка-приглашение создана!**\n"
        f"🌐 Язык: {lang_name}{desc_text}\n\n"
        f"🔗 Ссылка:\n{invite_link}\n\n"
        "Отправьте эту ссылку респонденту или в группу.\n"
        "Когда респондент заполнит анкету, вы получите файл .docx.",
        reply_markup=invite_created_keyboard(invite_link),
        parse_mode="Markdown"
    )
    
    await state.clear()


# ============ List Invites ============

@router.callback_query(F.data == "operator:my_invites")
async def list_my_invites(callback: CallbackQuery):
    """Show operator's invites as clickable list."""
    if not await is_operator(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    operator_id = await get_operator_id(callback.from_user.id)
    invites = await db.list_operator_invites(operator_id)
    
    if not invites:
        await callback.message.edit_text(
            "📭 У вас пока нет созданных приглашений.\n\n"
            "Нажмите «Создать ссылку-приглашение» чтобы создать первое.",
            reply_markup=operator_menu()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "📋 **Ваши приглашения:**\n\n"
        "Нажмите на приглашение, чтобы посмотреть анкеты.\n"
        "✅ = есть заполненные, ⏳ = ожидает заполнения",
        reply_markup=invites_list_keyboard(invites),
        parse_mode="Markdown"
    )
    await callback.answer()


# ============ Invite Detail ============

@router.callback_query(F.data.startswith("invite:"))
async def view_invite_detail(callback: CallbackQuery, bot: Bot):
    """View invite details with list of questionnaires."""
    if not await is_operator(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    invite_id = int(callback.data.split(":")[1])
    invite = await db.get_invite_by_id(invite_id)
    
    if not invite:
        await callback.answer("❌ Приглашение не найдено", show_alert=True)
        return
    
    # Get questionnaires for this invite
    questionnaires = await db.get_questionnaires_by_invite(invite_id)
    
    # Build invite link
    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start={invite['invite_code']}"
    
    desc = invite.get('description') or "Без описания"
    lang = invite.get('language', 'en')
    lang_name = LANGUAGES.get(lang, lang)
    
    completed = sum(1 for q in questionnaires if q['status'] == 'completed')
    in_progress = sum(1 for q in questionnaires if q['status'] == 'in_progress')
    
    text = (
        f"📋 **Приглашение:** {desc}\n"
        f"🌐 Язык: {lang_name}\n"
        f"🔗 `{invite_link}`\n\n"
        f"📊 Статистика:\n"
        f"✅ Заполнено: {completed}\n"
        f"⏳ В процессе: {in_progress}\n\n"
    )
    
    if questionnaires:
        text += "**Анкеты** (нажмите для скачивания):"
    else:
        text += "Пока никто не начал заполнять анкету."
    
    await callback.message.edit_text(
        text,
        reply_markup=invite_detail_keyboard(invite_id, questionnaires),
        parse_mode="Markdown"
    )
    await callback.answer()


# ============ Download Questionnaire ============

@router.callback_query(F.data.startswith("download_q:"))
async def download_questionnaire(callback: CallbackQuery, bot: Bot):
    """Download completed questionnaire as docx."""
    if not await is_operator(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    questionnaire_id = int(callback.data.split(":")[1])
    questionnaire = await db.get_questionnaire_by_id(questionnaire_id)
    
    if not questionnaire:
        await callback.answer("❌ Анкета не найдена", show_alert=True)
        return
    
    if questionnaire['status'] != 'completed':
        await callback.answer("⏳ Анкета ещё не заполнена", show_alert=True)
        return
    
    # Generate document
    questions = await db.get_all_questions()
    language = questionnaire.get('language', 'en')
    doc_path = await generate_questionnaire_docx(questionnaire, questions, language)
    
    respondent_name = questionnaire.get('respondent_name', 'Unknown')
    respondent_username = questionnaire.get('respondent_username')
    if respondent_username:
        respondent_name += f" (@{respondent_username})"
    
    # Send document
    document = FSInputFile(doc_path)
    await bot.send_document(
        chat_id=callback.from_user.id,
        document=document,
        caption=f"📄 Анкета от: {respondent_name}\n📅 Дата: {questionnaire.get('completed_at', 'N/A')}"
    )
    
    await callback.answer("📄 Файл отправлен!")


# ============ Questionnaire Info ============

@router.callback_query(F.data.startswith("q_info:"))
async def questionnaire_info(callback: CallbackQuery):
    """Show info about incomplete/cancelled questionnaire."""
    questionnaire_id = int(callback.data.split(":")[1])
    questionnaire = await db.get_questionnaire_by_id(questionnaire_id)
    
    if not questionnaire:
        await callback.answer("❌ Анкета не найдена", show_alert=True)
        return
    
    status_text = {
        'in_progress': '⏳ В процессе заполнения',
        'cancelled': '❌ Отменена респондентом',
        'completed': '✅ Завершена'
    }.get(questionnaire['status'], questionnaire['status'])
    
    respondent_name = questionnaire.get('respondent_name', 'Unknown')
    respondent_username = questionnaire.get('respondent_username')
    if respondent_username:
        respondent_name += f" (@{respondent_username})"
    
    # Count answered questions
    answers = await db.get_questionnaire_answers(questionnaire_id)
    questions = await db.get_all_questions()
    answered = len(answers)
    total = len(questions)
    
    await callback.answer(
        f"👤 {respondent_name}\n"
        f"📊 {status_text}\n"
        f"📝 Отвечено: {answered}/{total}",
        show_alert=True
    )


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Do nothing - placeholder callback."""
    await callback.answer()


# ============ All Questionnaires ============

async def is_admin(user_telegram_id: int) -> bool:
    """Check if user is admin."""
    user = await db.get_user_by_telegram_id(user_telegram_id)
    return user is not None and user.get('is_admin') == 1


@router.callback_query(F.data == "operator:all_questionnaires")
async def list_all_questionnaires(callback: CallbackQuery, state: FSMContext):
    """Show all questionnaires for operator (or ALL for admin)."""
    if not await is_operator(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    user_is_admin = await is_admin(callback.from_user.id)
    
    if user_is_admin:
        # Admin sees ALL questionnaires from all operators
        counts = await db.count_all_questionnaires_admin()
        questionnaires = await db.get_all_questionnaires_admin()
        title = "📄 **Все анкеты системы:**"
    else:
        # Operator sees only their own
        operator_id = await get_operator_id(callback.from_user.id)
        counts = await db.count_operator_questionnaires(operator_id)
        questionnaires = await db.get_all_operator_questionnaires(operator_id)
        title = "📄 **Все ваши анкеты:**"
    
    # Store in state for pagination
    await state.update_data(all_questionnaires=questionnaires, q_filter=None, is_admin_view=user_is_admin)
    
    if not questionnaires:
        await callback.message.edit_text(
            "📭 Анкет пока нет.\n\n"
            "Создайте приглашение и отправьте его респонденту.",
            reply_markup=operator_menu()
        )
        await callback.answer()
        return
    
    text = (
        f"{title}\n\n"
        f"📊 Статистика:\n"
        f"✅ Заполнено: {counts['completed']}\n"
        f"⏳ В процессе: {counts['in_progress']}\n"
        f"❌ Отменено: {counts['cancelled']}\n"
        f"📝 Всего: {counts['total']}\n\n"
        f"Нажмите на анкету для скачивания:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=all_questionnaires_keyboard(questionnaires, show_operator=user_is_admin),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("all_q_page:"))
async def all_questionnaires_page(callback: CallbackQuery, state: FSMContext):
    """Handle pagination for all questionnaires."""
    if not await is_operator(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    questionnaires = data.get('all_questionnaires', [])
    is_admin_view = data.get('is_admin_view', False)
    
    if not questionnaires:
        # Reload from DB
        q_filter = data.get('q_filter')
        if is_admin_view:
            questionnaires = await db.get_all_questionnaires_admin(q_filter)
        else:
            operator_id = await get_operator_id(callback.from_user.id)
            questionnaires = await db.get_all_operator_questionnaires(operator_id, q_filter)
        await state.update_data(all_questionnaires=questionnaires)
    
    await callback.message.edit_reply_markup(
        reply_markup=all_questionnaires_keyboard(questionnaires, page, show_operator=is_admin_view)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("all_q_filter:"))
async def filter_all_questionnaires(callback: CallbackQuery, state: FSMContext):
    """Filter questionnaires by status or show operator filter."""
    if not await is_operator(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    filter_type = callback.data.split(":")[1]
    data = await state.get_data()
    is_admin_view = data.get('is_admin_view', False)
    
    # Show operator filter menu
    if filter_type == 'by_operator' and is_admin_view:
        operators = await db.get_operators_with_questionnaire_counts()
        await callback.message.edit_text(
            "👤 **Выберите оператора:**\n\n"
            "Показаны операторы с анкетами.\n"
            "✅ — заполненные / всего",
            reply_markup=operators_filter_keyboard(operators),
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    # Apply status filter
    status_filter = 'completed' if filter_type == 'completed' else None
    operator_filter = data.get('operator_filter')  # Keep operator filter if set
    
    if is_admin_view:
        if operator_filter:
            questionnaires = await db.get_all_operator_questionnaires(operator_filter, status_filter)
            counts = await db.count_operator_questionnaires(operator_filter)
            # Get operator username for title
            operators = await db.get_operators_with_questionnaire_counts()
            op_name = next((o['username'] for o in operators if o['id'] == operator_filter), '?')
            title = f"📄 **Анкеты @{op_name}"
        else:
            questionnaires = await db.get_all_questionnaires_admin(status_filter)
            counts = await db.count_all_questionnaires_admin()
            title = "📄 **Анкеты системы"
    else:
        operator_id = await get_operator_id(callback.from_user.id)
        questionnaires = await db.get_all_operator_questionnaires(operator_id, status_filter)
        counts = await db.count_operator_questionnaires(operator_id)
        title = "📄 **Анкеты"
    
    # Store in state
    await state.update_data(all_questionnaires=questionnaires, q_filter=status_filter)
    
    filter_text = "✅ заполненные" if filter_type == 'completed' else "все"
    text = (
        f"{title} ({filter_text}):**\n\n"
        f"📊 Статистика:\n"
        f"✅ Заполнено: {counts['completed']}\n"
        f"⏳ В процессе: {counts['in_progress']}\n"
        f"❌ Отменено: {counts['cancelled']}\n"
        f"📝 Всего: {counts['total']}\n\n"
    )
    
    if questionnaires:
        text += "Нажмите на анкету для скачивания:"
    else:
        text += "Анкет с таким статусом нет."
    
    await callback.message.edit_text(
        text,
        reply_markup=all_questionnaires_keyboard(questionnaires, page=0, show_operator=is_admin_view),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("all_q_operator:"))
async def filter_by_operator(callback: CallbackQuery, state: FSMContext):
    """Filter questionnaires by specific operator (admin only)."""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Только для админов", show_alert=True)
        return
    
    operator_value = callback.data.split(":")[1]
    data = await state.get_data()
    status_filter = data.get('q_filter')
    
    if operator_value == 'all':
        # Show all operators' questionnaires
        questionnaires = await db.get_all_questionnaires_admin(status_filter)
        counts = await db.count_all_questionnaires_admin()
        title = "📄 **Все анкеты системы:**"
        await state.update_data(operator_filter=None)
    else:
        # Filter by specific operator
        operator_id = int(operator_value)
        questionnaires = await db.get_all_operator_questionnaires(operator_id, status_filter)
        counts = await db.count_operator_questionnaires(operator_id)
        
        # Get operator username
        operators = await db.get_operators_with_questionnaire_counts()
        op_name = next((o['username'] for o in operators if o['id'] == operator_id), '?')
        title = f"📄 **Анкеты оператора @{op_name}:**"
        await state.update_data(operator_filter=operator_id)
    
    await state.update_data(all_questionnaires=questionnaires, is_admin_view=True)
    
    text = (
        f"{title}\n\n"
        f"📊 Статистика:\n"
        f"✅ Заполнено: {counts['completed']}\n"
        f"⏳ В процессе: {counts['in_progress']}\n"
        f"❌ Отменено: {counts['cancelled']}\n"
        f"📝 Всего: {counts['total']}\n\n"
    )
    
    if questionnaires:
        text += "Нажмите на анкету для скачивания:"
    else:
        text += "Анкет нет."
    
    await callback.message.edit_text(
        text,
        reply_markup=all_questionnaires_keyboard(questionnaires, page=0, show_operator=True),
        parse_mode="Markdown"
    )
    await callback.answer()
