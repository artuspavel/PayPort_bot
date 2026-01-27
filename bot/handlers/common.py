"""Common handlers for all users."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from bot import database as db
from bot.keyboards import admin_menu, operator_menu, cancel_button
from bot.locales import get_text
from bot.config import FINGERPRINT_SERVER_URL

router = Router()


@router.callback_query(F.data == "start_after_verification")
async def start_after_verification_callback(callback: CallbackQuery, state: FSMContext):
    """Start questionnaire after verification (fallback if web_app_data didn't arrive)."""
    data = await state.get_data()
    invite = data.get('pending_invite')
    
    if not invite:
        invite_code = data.get('pending_invite_code')
        if invite_code:
            invite = await db.get_invite_by_code(invite_code)
        else:
            pending = await db.get_pending_verification(callback.from_user.id)
            if pending:
                invite = await db.get_invite_by_id(pending['invite_id'])
    
    if not invite:
        await callback.answer("❌ Session expired. Please use the invite link again.", show_alert=True)
        return
    
    # Get latest fingerprint for this user if not in state
    if not data.get('fingerprint_id'):
        fp = await db.get_fingerprint_by_telegram_id(callback.from_user.id)
        if fp:
            await state.update_data(fingerprint_id=fp['id'], check_fingerprint_matches=True)
    
    await callback.message.delete()
    language = invite.get('language', 'en')
    if language == 'ru':
        await callback.message.answer("✅ Верификация пройдена! Начинаем анкету...")
    elif language == 'ar':
        await callback.message.answer("✅ تم التحقق! بدء الاستبيان...")
    else:
        await callback.message.answer("✅ Verification complete! Starting questionnaire...")
    
    from bot.handlers.questionnaire import start_questionnaire_flow
    await start_questionnaire_flow(callback.message, invite, state)
    await db.clear_pending_verification(callback.from_user.id)
    await callback.answer()


@router.message(CommandStart(deep_link=True))
async def cmd_start_with_invite(message: Message, command: CommandStart, state: FSMContext):
    """Handle /start with invite code (deep link)."""
    invite_code = command.args
    
    if not invite_code:
        await cmd_start(message, state)
        return
    
    # Check if user is operator/admin - they shouldn't fill questionnaires
    user = await db.get_user_by_telegram_id(message.from_user.id)
    if user:
        await message.answer(
            "⚠️ You are registered as operator/admin.\n"
            "Operators cannot fill questionnaires.\n\n"
            "⚠️ Вы зарегистрированы как оператор/админ.\n"
            "Операторы не могут заполнять анкеты.",
            reply_markup=operator_menu() if not user['is_admin'] else admin_menu()
        )
        return
    
    # Check invite validity
    invite = await db.get_invite_by_code(invite_code)
    if not invite:
        await message.answer(
            "❌ Invalid invitation link. Please ask sender for a new link.\n\n"
            "❌ Недействительная ссылка-приглашение. Попросите отправителя создать новую."
        )
        return
    
    # Get language from invite
    language = invite.get('language', 'en')
    
    # Check if has incomplete questionnaire FOR THIS INVITE - can resume
    incomplete_for_invite = await db.get_incomplete_questionnaire_for_invite(
        message.from_user.id, invite['id']
    )
    
    if incomplete_for_invite:
        # Resume existing questionnaire
        from bot.handlers.questionnaire import resume_questionnaire_flow
        await resume_questionnaire_flow(message, invite, incomplete_for_invite, state)
        return
    
    # Check if has active questionnaire for DIFFERENT invite
    active_q = await db.get_active_questionnaire(message.from_user.id)
    if active_q and active_q.get('invite_id') != invite['id']:
        if language == 'ru':
            await message.answer(
                "⚠️ У вас уже есть незавершённая анкета по другой ссылке.\n"
                "Напишите /cancel чтобы отменить её и начать новую."
            )
        else:
            await message.answer(
                "⚠️ You have an incomplete questionnaire from another link.\n"
                "Type /cancel to cancel it and start a new one."
            )
        return
    
    # Store invite for later use after verification
    await state.update_data(pending_invite=invite, pending_invite_code=invite_code, waiting_for_verification=True)
    await db.save_pending_verification(message.from_user.id, invite['id'])
    
    # Show verification Web App button
    # NOTE: Web App collects device fingerprint for fraud detection
    if FINGERPRINT_SERVER_URL and FINGERPRINT_SERVER_URL != "https://payport.example.com":
        verify_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔐 Verify / Верификация",
                web_app=WebAppInfo(url=f"{FINGERPRINT_SERVER_URL}/fingerprint")
            )]
        ])
        
        if language == 'ru':
            await message.answer(
                "🔐 **Верификация устройства**\n\n"
                "Для начала анкеты нажмите кнопку ниже.\n"
                "Это займёт несколько секунд.",
                reply_markup=verify_keyboard,
                parse_mode="Markdown"
            )
        elif language == 'ar':
            await message.answer(
                "🔐 **التحقق من الجهاز**\n\n"
                "للبدء، اضغط على الزر أدناه.\n"
                "سيستغرق هذا بضع ثوانٍ.",
                reply_markup=verify_keyboard,
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                "🔐 **Device Verification**\n\n"
                "To start the questionnaire, tap the button below.\n"
                "This will take a few seconds.",
                reply_markup=verify_keyboard,
                parse_mode="Markdown"
            )
    else:
        # No fingerprint server configured - start directly
        from bot.handlers.questionnaire import start_questionnaire_flow
        await start_questionnaire_flow(message, invite, state)


@router.message(F.web_app_data)
async def handle_web_app_data(message: Message, state: FSMContext):
    """Handle data received from Web App (fingerprint verification).
    
    NOTE: Verification is mandatory - questionnaire starts only after successful verification.
    """
    import json
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        web_data = json.loads(message.web_app_data.data)
        logger.info(f"Web app data received: {web_data}")
    except Exception as e:
        logger.error(f"Error parsing web app data: {e}")
        web_data = {}
    
    data = await state.get_data()
    invite = data.get('pending_invite')
    
    if not invite:
        logger.warning("No pending_invite in state")
        # Try to get invite from invite_code
        invite_code = data.get('pending_invite_code')
        if invite_code:
            invite = await db.get_invite_by_code(invite_code)
        else:
            pending = await db.get_pending_verification(message.from_user.id)
            if pending:
                invite = await db.get_invite_by_id(pending['invite_id'])
        
        if not invite:
            await message.answer("❌ Session expired. Please use the invite link again.")
            return
    
    language = invite.get('language', 'en')
    
    # Check if verification was successful
    if not web_data.get('verified'):
        logger.warning(f"Verification failed: {web_data}")
        # Verification failed - don't start questionnaire
        if language == 'ru':
            await message.answer(
                "❌ **Верификация не пройдена**\n\n"
                "Пожалуйста, попробуйте ещё раз. Верификация обязательна для заполнения анкеты."
            )
        elif language == 'ar':
            await message.answer(
                "❌ **فشل التحقق**\n\n"
                "يرجى المحاولة مرة أخرى. التحقق إلزامي لملء الاستبيان."
            )
        else:
            await message.answer(
                "❌ **Verification failed**\n\n"
                "Please try again. Verification is required to fill the questionnaire."
            )
        return
    
    logger.info(f"Verification successful, fp_id: {web_data.get('fp_id')}")
    
    # Verification successful - get fingerprint ID
    fp_id = web_data.get('fp_id')
    if not fp_id:
        # Fallback: get latest fingerprint for this user
        logger.warning("No fp_id in web_data, trying to get latest fingerprint")
        fp = await db.get_fingerprint_by_telegram_id(message.from_user.id)
        if fp:
            fp_id = fp['id']
            logger.info(f"Found fingerprint ID: {fp_id}")
    
    if fp_id:
        await state.update_data(fingerprint_id=fp_id)
    
    # Check for matches and notify later when questionnaire is created
    await state.update_data(check_fingerprint_matches=True, waiting_for_verification=False)
    
    # Notify user and start questionnaire automatically
    if language == 'ru':
        await message.answer("✅ Верификация пройдена! Начинаем анкету...")
    elif language == 'ar':
        await message.answer("✅ تم التحقق! بدء الاستبيان...")
    else:
        await message.answer("✅ Verification complete! Starting questionnaire...")
    
    # Start questionnaire automatically after verification
    logger.info(f"Starting questionnaire flow for invite {invite.get('id')}")
    from bot.handlers.questionnaire import start_questionnaire_flow
    await start_questionnaire_flow(message, invite, state)
    await db.clear_pending_verification(message.from_user.id)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command without parameters."""
    await state.clear()
    
    username = message.from_user.username
    
    if not username:
        await message.answer(
            "⚠️ You don't have a Telegram username set.\n"
            "Please set a username in Telegram settings and try again.\n\n"
            "⚠️ У вас не установлен username в Telegram.\n"
            "Установите username в настройках и попробуйте снова."
        )
        return
    
    # Check if user is registered operator/admin
    user = await db.get_user_by_username(username)
    
    if user:
        # Update telegram_id if not set
        if not user['telegram_id']:
            await db.update_user_telegram_id(username, message.from_user.id)
        
        if user['is_admin']:
            await message.answer(
                f"👑 Добро пожаловать, администратор @{username}!\n\n"
                "Выберите действие:",
                reply_markup=admin_menu()
            )
        else:
            await message.answer(
                f"👤 Добро пожаловать, оператор @{username}!\n\n"
                "Выберите действие:",
                reply_markup=operator_menu()
            )
    else:
        # Check if has active questionnaire
        active_q = await db.get_active_questionnaire(message.from_user.id)
        if active_q:
            await message.answer(
                "⚠️ You have an incomplete questionnaire.\n"
                "Type /cancel to cancel it and start fresh.\n\n"
                "⚠️ У вас есть незавершённая анкета.\n"
                "Напишите /cancel чтобы отменить её."
            )
            return
        
        await message.answer(
            "👋 Hello! / Привет!\n\n"
            "This bot is for filling questionnaires.\n"
            "If you received a link — follow it to start.\n\n"
            "Этот бот для заполнения анкет.\n"
            "Если вам прислали ссылку — перейдите по ней."
        )


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    """Show menu for registered users."""
    await state.clear()
    
    user = await db.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer(
            "❌ You are not registered in the system.\n"
            "❌ Вы не зарегистрированы в системе."
        )
        return
    
    if user['is_admin']:
        await message.answer("👑 Меню администратора:", reply_markup=admin_menu())
    else:
        await message.answer("👤 Меню оператора:", reply_markup=operator_menu())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Cancel current operation and incomplete questionnaire."""
    await state.clear()
    
    # Also cancel any incomplete questionnaire in DB
    cancelled = await db.cancel_questionnaire(message.from_user.id)
    
    if cancelled:
        await message.answer(
            "✅ Questionnaire cancelled. You can start a new one.\n"
            "✅ Анкета отменена. Можете начать новую."
        )
    else:
        await message.answer(
            "❌ Operation cancelled.\n"
            "❌ Операция отменена."
        )


@router.callback_query(F.data == "cancel")
async def callback_cancel(callback: CallbackQuery, state: FSMContext):
    """Cancel callback."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Operation cancelled.\n"
        "❌ Операция отменена."
    )
    await callback.answer()


@router.callback_query(F.data == "main:start")
async def callback_main_start(callback: CallbackQuery, state: FSMContext):
    """Return to start - show main menu based on user role."""
    await state.clear()
    
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    
    if user:
        if user['is_admin']:
            await callback.message.edit_text(
                f"👑 Главное меню администратора @{user['username']}",
                reply_markup=admin_menu()
            )
        else:
            await callback.message.edit_text(
                f"👤 Главное меню оператора @{user['username']}",
                reply_markup=operator_menu()
            )
    else:
        await callback.message.edit_text(
            "👋 Hello! / Привет!\n\n"
            "This bot is for filling questionnaires.\n"
            "If you received a link — follow it to start.\n\n"
            "Этот бот для заполнения анкет.\n"
            "Если вам прислали ссылку — перейдите по ней."
        )
    
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Show help message."""
    user = await db.get_user_by_telegram_id(message.from_user.id)
    
    if user and user['is_admin']:
        help_text = (
            "👑 **Команды администратора:**\n\n"
            "/menu - Показать меню\n"
            "/cancel - Отменить текущую операцию\n\n"
            "**Функции:**\n"
            "• Добавление/удаление операторов\n"
            "• Назначение админов\n"
            "• Редактирование вопросов анкеты\n"
            "• Создание ссылок-приглашений"
        )
    elif user:
        help_text = (
            "👤 **Команды оператора:**\n\n"
            "/menu - Показать меню\n"
            "/cancel - Отменить текущую операцию\n\n"
            "**Функции:**\n"
            "• Создание ссылок-приглашений\n"
            "• Просмотр своих приглашений\n"
            "• Получение заполненных анкет"
        )
    else:
        help_text = (
            "👋 **Help / Помощь:**\n\n"
            "EN: This bot is for filling questionnaires.\n"
            "If you received a link — follow it.\n"
            "/cancel - Cancel current questionnaire\n\n"
            "RU: Бот для заполнения анкет.\n"
            "Если прислали ссылку — перейдите по ней.\n"
            "/cancel - Отменить анкету"
        )
    
    await message.answer(help_text, parse_mode="Markdown")
