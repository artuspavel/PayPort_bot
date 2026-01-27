"""Questionnaire handlers for respondents."""
import json
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from bot import database as db
from bot.states import QuestionnaireStates
from bot.document_generator import generate_questionnaire_docx
from bot.locales import get_text, LANGUAGES, PASSPORT_EXAMPLE_URL, SELFIE_EXAMPLE_URL

router = Router()


def get_question_text(question: dict, language: str) -> str:
    """Get question text in specified language."""
    text = question.get('text', '')
    
    # Try to parse as JSON (new format with ru/en)
    try:
        texts = json.loads(text)
        return texts.get(language, texts.get('en', text))
    except (json.JSONDecodeError, TypeError):
        # Old format - plain text
        return text


async def start_questionnaire_flow(message: Message, invite: dict, state: FSMContext):
    """Start questionnaire for respondent."""
    # Get language from invite
    language = invite.get('language', 'en')
    
    # Get all questions
    questions = await db.get_all_questions()
    
    if not questions:
        await message.answer(get_text(language, "questions_not_found"))
        return
    
    # Create questionnaire record
    questionnaire_id = await db.start_questionnaire(
        invite_id=invite['id'],
        respondent_telegram_id=message.from_user.id,
        respondent_username=message.from_user.username or "unknown",
        respondent_name=message.from_user.full_name
    )
    
    # Clear pending verification once questionnaire starts
    await db.clear_pending_verification(message.from_user.id)
    
    # Link fingerprint to questionnaire if exists
    state_data = await state.get_data()
    fingerprint_id = state_data.get('fingerprint_id')
    fingerprint_matches = []
    
    if fingerprint_id:
        await db.link_fingerprint_to_questionnaire(fingerprint_id, questionnaire_id)
        
        # Check for fingerprint matches
        if state_data.get('check_fingerprint_matches'):
            fp = await db.get_fingerprint_by_telegram_id(message.from_user.id)
            if fp:
                fingerprint_matches = await db.find_matching_fingerprints(fp, exclude_telegram_id=message.from_user.id)
    
    # Store state data
    await state.set_state(QuestionnaireStates.answering)
    await state.update_data(
        questionnaire_id=questionnaire_id,
        questions=questions,
        current_question_index=0,
        invite=invite,
        language=language,
        media_files=[],  # Store media file_ids
        operator_telegram_id=invite.get('operator_telegram_id'),
        respondent_name=message.from_user.full_name,
        respondent_username=message.from_user.username,
        fingerprint_matches=fingerprint_matches  # Store for later notification
    )
    
    # Welcome message
    topic_text = ""
    if invite.get('description'):
        topic_text = f"\n{get_text(language, 'topic')}: {invite.get('description')}"
    
    media_hint = get_text(language, 'media_hint')
    
    await message.answer(
        f"{get_text(language, 'welcome_questionnaire')}{topic_text}\n\n"
        f"{get_text(language, 'questions_count', count=len(questions))}\n"
        f"{get_text(language, 'answer_instruction')}\n"
        f"{media_hint}\n\n"
        f"{get_text(language, 'cancel_instruction')}\n\n"
        f"{get_text(language, 'lets_start')}"
    )
    
    # Send first question
    await send_question(message, questions[0], 1, len(questions), language)


async def resume_questionnaire_flow(message: Message, invite: dict, questionnaire: dict, state: FSMContext):
    """Resume incomplete questionnaire for respondent.
    
    NOTE: Allows respondent to continue from where they left off.
    """
    language = invite.get('language', 'en')
    
    # Get all questions
    questions = await db.get_all_questions()
    
    if not questions:
        await message.answer(get_text(language, "questions_not_found"))
        return
    
    # Get existing answers to determine progress
    answers = await db.get_questionnaire_answers(questionnaire['id'])
    
    # Find first unanswered question
    current_index = 0
    for i, q in enumerate(questions):
        if q['key'] not in answers:
            current_index = i
            break
    else:
        # All questions answered - this shouldn't happen but handle it
        current_index = len(questions) - 1
    
    # Store state data
    await state.set_state(QuestionnaireStates.answering)
    await state.update_data(
        questionnaire_id=questionnaire['id'],
        questions=questions,
        current_question_index=current_index,
        invite=invite,
        language=language,
        media_files=[],
        operator_telegram_id=invite.get('operator_telegram_id'),
        respondent_name=message.from_user.full_name,
        respondent_username=message.from_user.username
    )
    
    answered = len(answers)
    total = len(questions)
    
    # Resume message
    if language == 'ru':
        await message.answer(
            f"👋 С возвращением!\n\n"
            f"📝 Вы уже ответили на {answered} из {total} вопросов.\n"
            f"Продолжим с вопроса {current_index + 1}.\n\n"
            f"Для отмены используйте /cancel"
        )
    else:
        await message.answer(
            f"👋 Welcome back!\n\n"
            f"📝 You have answered {answered} of {total} questions.\n"
            f"Continuing from question {current_index + 1}.\n\n"
            f"Use /cancel to abort"
        )
    
    # Send current question
    await send_question(message, questions[current_index], current_index + 1, total, language)


async def send_question(message: Message, question: dict, number: int, total: int, language: str):
    """Send question to respondent."""
    question_text = get_question_text(question, language)
    header = get_text(language, 'question_of', current=number, total=total)
    # NOTE: Using HTML to avoid Markdown parsing issues with special chars in questions
    await message.answer(
        f"<b>{header}</b>\n\n"
        f"{question_text}",
        parse_mode="HTML"
    )


@router.message(QuestionnaireStates.answering, F.photo)
async def process_photo_answer(message: Message, state: FSMContext, bot: Bot):
    """Process photo answer from respondent."""
    data = await state.get_data()
    
    questionnaire_id = data['questionnaire_id']
    questions = data['questions']
    current_index = data['current_question_index']
    language = data.get('language', 'en')
    media_files = data.get('media_files', [])
    
    current_question = questions[current_index]
    
    # Get the largest photo
    photo = message.photo[-1]
    file_id = photo.file_id
    
    # Save photo file_id to media list
    media_files.append({
        'type': 'photo',
        'file_id': file_id,
        'question_key': current_question['key'],
        'question_text': get_question_text(current_question, language)
    })
    
    # Save answer as text reference
    caption = message.caption or ""
    answer = f"[📷 Photo uploaded] {caption}".strip()
    await db.save_answer(questionnaire_id, current_question['key'], answer)
    
    # Update state with media
    await state.update_data(media_files=media_files)
    
    # Confirm receipt
    await message.answer(get_text(language, "photo_received"))
    
    # Move to next question
    await move_to_next_question(message, state, bot, data)


@router.message(QuestionnaireStates.answering, F.video)
async def process_video_answer(message: Message, state: FSMContext, bot: Bot):
    """Process video answer from respondent."""
    data = await state.get_data()
    
    questionnaire_id = data['questionnaire_id']
    questions = data['questions']
    current_index = data['current_question_index']
    language = data.get('language', 'en')
    media_files = data.get('media_files', [])
    
    current_question = questions[current_index]
    
    # Get video file_id
    video = message.video
    file_id = video.file_id
    
    # Save video file_id to media list
    media_files.append({
        'type': 'video',
        'file_id': file_id,
        'question_key': current_question['key'],
        'question_text': get_question_text(current_question, language)
    })
    
    # Save answer as text reference
    caption = message.caption or ""
    answer = f"[🎥 Video uploaded] {caption}".strip()
    await db.save_answer(questionnaire_id, current_question['key'], answer)
    
    # Update state with media
    await state.update_data(media_files=media_files)
    
    # Confirm receipt
    await message.answer(get_text(language, "video_received"))
    
    # Move to next question
    await move_to_next_question(message, state, bot, data)


@router.message(QuestionnaireStates.answering, F.document)
async def process_document_answer(message: Message, state: FSMContext, bot: Bot):
    """Process document answer from respondent."""
    data = await state.get_data()
    
    questionnaire_id = data['questionnaire_id']
    questions = data['questions']
    current_index = data['current_question_index']
    language = data.get('language', 'en')
    media_files = data.get('media_files', [])
    
    current_question = questions[current_index]
    
    # Get document file_id
    document = message.document
    file_id = document.file_id
    file_name = document.file_name or "document"
    
    # Save document file_id to media list
    media_files.append({
        'type': 'document',
        'file_id': file_id,
        'file_name': file_name,
        'question_key': current_question['key'],
        'question_text': get_question_text(current_question, language)
    })
    
    # Save answer as text reference
    caption = message.caption or ""
    answer = f"[📎 Document: {file_name}] {caption}".strip()
    await db.save_answer(questionnaire_id, current_question['key'], answer)
    
    # Update state with media
    await state.update_data(media_files=media_files)
    
    # Confirm receipt
    await message.answer(get_text(language, "document_received"))
    
    # Move to next question
    await move_to_next_question(message, state, bot, data)


@router.message(QuestionnaireStates.answering)
async def process_text_answer(message: Message, state: FSMContext, bot: Bot):
    """Process text answer from respondent."""
    data = await state.get_data()
    
    questionnaire_id = data['questionnaire_id']
    questions = data['questions']
    current_index = data['current_question_index']
    language = data.get('language', 'en')
    
    current_question = questions[current_index]
    answer = message.text.strip() if message.text else ""
    
    if not answer:
        await message.answer(get_text(language, "empty_answer_warning"))
        return
    
    # Save answer
    await db.save_answer(questionnaire_id, current_question['key'], answer)
    
    # Move to next question
    await move_to_next_question(message, state, bot, data)


async def move_to_next_question(message: Message, state: FSMContext, bot: Bot, data: dict):
    """Move to next question or complete questionnaire."""
    questions = data['questions']
    current_index = data['current_question_index']
    invite = data['invite']
    language = data.get('language', 'en')
    questionnaire_id = data['questionnaire_id']
    
    next_index = current_index + 1
    
    if next_index < len(questions):
        # More questions left
        await state.update_data(current_question_index=next_index)
        await send_question(message, questions[next_index], next_index + 1, len(questions), language)
    else:
        # Questionnaire completed - send to operator and start verification
        updated_data = await state.get_data()
        media_files = updated_data.get('media_files', [])
        await complete_questionnaire_and_start_verification(
            message, state, bot, questionnaire_id, invite, language, media_files
        )


async def complete_questionnaire_and_start_verification(
    message: Message, state: FSMContext, bot: Bot,
    questionnaire_id: int, invite: dict, language: str, media_files: list
):
    """Complete questionnaire, send to operator, then start passport verification."""
    # Mark as completed and get full data
    questionnaire_data = await db.complete_questionnaire(questionnaire_id)
    questions = await db.get_all_questions()
    
    # Thank respondent for questionnaire
    await message.answer(
        get_text(language, "thank_you"),
        parse_mode="Markdown"
    )
    
    # Generate document
    doc_path = await generate_questionnaire_docx(questionnaire_data, questions, language)
    
    # Send document to operator
    operator_telegram_id = questionnaire_data.get('operator_telegram_id')
    respondent_info = questionnaire_data.get('respondent_name', 'Unknown')
    respondent_username = questionnaire_data.get('respondent_username')
    if respondent_username:
        respondent_info += f" (@{respondent_username})"
    
    if operator_telegram_id:
        invite_desc = questionnaire_data.get('invite_description')
        lang_flag = "🇷🇺" if language == "ru" else "🇬🇧" if language == "en" else "🇸🇦"
        desc_text = f"\n📝 Тема: {invite_desc}" if invite_desc else ""
        
        # Get fingerprint data for this questionnaire
        state_data = await state.get_data()
        fingerprint_id = state_data.get('fingerprint_id')
        fingerprint_data = None
        fingerprint_matches = []
        
        if fingerprint_id:
            # Get fingerprint by ID
            fingerprint_data = await db.get_fingerprint_by_id(fingerprint_id)
        else:
            # Try to get latest fingerprint for this user
            fingerprint_data = await db.get_fingerprint_by_telegram_id(message.from_user.id)
        
        # Find matches if fingerprint exists
        if fingerprint_data:
            fp_raw = json.loads(fingerprint_data.get('raw_data', '{}'))
            fingerprint_matches = await db.find_matching_fingerprints(
                fp_raw,
                exclude_telegram_id=message.from_user.id
            )
        
        try:
            # Send fingerprint verification info to operator
            if fingerprint_data:
                fp_info = json.loads(fingerprint_data.get('raw_data', '{}'))
                
                fp_text = (
                    f"🔐 **Информация о верификации устройства:**\n\n"
                    f"👤 Респондент: {respondent_info}\n"
                    f"🌐 IP адрес: `{fp_info.get('ip_address', 'N/A')}`\n"
                    f"📱 Платформа: {fp_info.get('platform', 'N/A')}\n"
                    f"🖥 Разрешение: {fp_info.get('screen_resolution', 'N/A')}\n"
                    f"🌍 Часовой пояс: {fp_info.get('timezone', 'N/A')}\n"
                    f"🌐 Язык: {fp_info.get('language', 'N/A')}\n"
                )
                
                # Add matches info
                if fingerprint_matches:
                    fp_text += f"\n⚠️ **ОБНАРУЖЕНЫ СОВПАДЕНИЯ ({len(fingerprint_matches)}):**\n\n"
                    
                    # Group by match type
                    by_type = {}
                    for match in fingerprint_matches:
                        match_type = match.get('match_type', 'unknown')
                        if match_type not in by_type:
                            by_type[match_type] = []
                        by_type[match_type].append(match)
                    
                    type_names = {
                        'ip_address': '🌐 Совпадение IP адреса',
                        'canvas_hash': '🖥 Совпадение устройства (Canvas)',
                        'device_combo': '📱 Совпадение профиля устройства'
                    }
                    
                    seen_users = set()
                    for match_type, matches in by_type.items():
                        type_name = type_names.get(match_type, f'❓ {match_type}')
                        fp_text += f"**{type_name}:**\n"
                        
                        for match in matches[:3]:  # Max 3 per type
                            match_user = match.get('respondent_username')
                            match_name = match.get('respondent_name', 'Unknown')
                            match_q_status = match.get('q_status', 'unknown')
                            match_desc = match.get('invite_description') or "Без темы"
                            
                            if match_user:
                                user_display = f"@{match_user}"
                            else:
                                user_display = f"{match_name} (ID:{match.get('telegram_id')})"
                            
                            if user_display not in seen_users:
                                status_icon = "✅" if match_q_status == 'completed' else "⏳" if match_q_status == 'in_progress' else "❌"
                                fp_text += f"  {status_icon} {user_display} — {match_desc}\n"
                                seen_users.add(user_display)
                        
                        if len(matches) > 3:
                            fp_text += f"  ...и ещё {len(matches) - 3}\n"
                        fp_text += "\n"
                else:
                    fp_text += "\n✅ Совпадений не обнаружено"
                
                await bot.send_message(
                    chat_id=operator_telegram_id,
                    text=fp_text,
                    parse_mode="Markdown"
                )
            else:
                # No fingerprint - send warning
                await bot.send_message(
                    chat_id=operator_telegram_id,
                    text=(
                        f"⚠️ **Внимание:**\n\n"
                        f"Анкета от {respondent_info} заполнена БЕЗ верификации устройства.\n"
                        f"Возможно, fingerprint сервер был недоступен или пользователь обошёл проверку."
                    ),
                    parse_mode="Markdown"
                )
            
            # Send main document
            document = FSInputFile(doc_path)
            await bot.send_document(
                chat_id=operator_telegram_id,
                document=document,
                caption=(
                    f"📄 **Новая заполненная анкета!** {lang_flag}{desc_text}\n\n"
                    f"👤 Респондент: {respondent_info}\n"
                    f"📅 Дата: {questionnaire_data.get('completed_at', 'N/A')}\n\n"
                    f"⏳ Ожидаем документы верификации..."
                ),
                parse_mode="Markdown"
            )
            
            # Send all media files from questionnaire
            if media_files:
                await bot.send_message(
                    chat_id=operator_telegram_id,
                    text=f"📎 **Прикреплённые файлы от {respondent_info}:**",
                    parse_mode="Markdown"
                )
                
                for media in media_files:
                    question_text = media.get('question_text', '')[:100]
                    caption = f"📌 К вопросу: {question_text}"
                    
                    try:
                        if media['type'] == 'photo':
                            await bot.send_photo(
                                chat_id=operator_telegram_id,
                                photo=media['file_id'],
                                caption=caption
                            )
                        elif media['type'] == 'video':
                            await bot.send_video(
                                chat_id=operator_telegram_id,
                                video=media['file_id'],
                                caption=caption
                            )
                        elif media['type'] == 'document':
                            await bot.send_document(
                                chat_id=operator_telegram_id,
                                document=media['file_id'],
                                caption=caption
                            )
                    except Exception as e:
                        print(f"Error sending media to operator: {e}")
                        
        except Exception as e:
            print(f"Error sending document to operator: {e}")
    
    # Store data for verification phase
    await state.update_data(
        operator_telegram_id=operator_telegram_id,
        respondent_info=respondent_info
    )
    
    # Start passport verification
    await start_passport_verification(message, state, language)


async def start_passport_verification(message: Message, state: FSMContext, language: str):
    """Start passport verification process."""
    # Send intro message
    await message.answer(
        get_text(language, "verification_intro"),
        parse_mode="Markdown"
    )
    
    # Request passport photo with example
    await message.answer(
        get_text(language, "passport_photo_request"),
        parse_mode="Markdown"
    )
    
    # Send example image
    try:
        await message.answer_photo(
            photo=PASSPORT_EXAMPLE_URL,
            caption="📷 Example / Пример"
        )
    except:
        pass  # If example image fails, continue without it
    
    # Set state to waiting for passport photo
    await state.set_state(QuestionnaireStates.waiting_passport_photo)


# ============ Passport Photo Handler ============

@router.message(QuestionnaireStates.waiting_passport_photo, F.photo)
async def process_passport_photo(message: Message, state: FSMContext, bot: Bot):
    """Process passport photo from respondent."""
    data = await state.get_data()
    language = data.get('language', 'en')
    
    # Get the largest photo
    photo = message.photo[-1]
    passport_photo_id = photo.file_id
    
    # Store passport photo
    await state.update_data(passport_photo_id=passport_photo_id)
    
    # Confirm receipt
    await message.answer(get_text(language, "passport_photo_received"))
    
    # Request selfie video with passport
    await message.answer(
        get_text(language, "passport_selfie_request"),
        parse_mode="Markdown"
    )
    
    # Send example image
    try:
        await message.answer_photo(
            photo=SELFIE_EXAMPLE_URL,
            caption="🎥 Example / Пример"
        )
    except:
        pass
    
    # Set state to waiting for selfie video
    await state.set_state(QuestionnaireStates.waiting_passport_selfie)


@router.message(QuestionnaireStates.waiting_passport_photo)
async def waiting_passport_photo_invalid(message: Message, state: FSMContext):
    """Handle non-photo messages when waiting for passport photo."""
    data = await state.get_data()
    language = data.get('language', 'en')
    await message.answer(get_text(language, "waiting_photo"))


# ============ Passport Selfie Video Handler ============

@router.message(QuestionnaireStates.waiting_passport_selfie, F.video)
async def process_passport_selfie_video(message: Message, state: FSMContext, bot: Bot):
    """Process selfie video with passport."""
    data = await state.get_data()
    language = data.get('language', 'en')
    operator_telegram_id = data.get('operator_telegram_id')
    respondent_info = data.get('respondent_info', 'Unknown')
    passport_photo_id = data.get('passport_photo_id')
    
    # Get video file_id
    video = message.video
    selfie_video_id = video.file_id
    
    # Confirm receipt
    await message.answer(get_text(language, "passport_selfie_received"))
    
    # Send verification complete message
    await message.answer(
        get_text(language, "verification_complete"),
        parse_mode="Markdown"
    )
    
    # Send verification documents to operator
    if operator_telegram_id:
        try:
            # Header message
            await bot.send_message(
                chat_id=operator_telegram_id,
                text=f"🔐 **{get_text(language, 'verification_docs')}**\n\n"
                     f"👤 От: {respondent_info}",
                parse_mode="Markdown"
            )
            
            # Send passport photo
            if passport_photo_id:
                await bot.send_photo(
                    chat_id=operator_telegram_id,
                    photo=passport_photo_id,
                    caption=f"📸 {get_text(language, 'passport_photo_caption')}\n👤 {respondent_info}"
                )
            
            # Send selfie video
            await bot.send_video(
                chat_id=operator_telegram_id,
                video=selfie_video_id,
                caption=f"🎥 {get_text(language, 'passport_selfie_caption')}\n👤 {respondent_info}"
            )
            
        except Exception as e:
            print(f"Error sending verification docs to operator: {e}")
    
    # Clear state - verification complete
    await state.clear()


@router.message(QuestionnaireStates.waiting_passport_selfie, F.video_note)
async def process_passport_selfie_video_note(message: Message, state: FSMContext, bot: Bot):
    """Process video note (circle video) as selfie."""
    data = await state.get_data()
    language = data.get('language', 'en')
    operator_telegram_id = data.get('operator_telegram_id')
    respondent_info = data.get('respondent_info', 'Unknown')
    passport_photo_id = data.get('passport_photo_id')
    
    # Get video note file_id
    video_note = message.video_note
    selfie_video_id = video_note.file_id
    
    # Confirm receipt
    await message.answer(get_text(language, "passport_selfie_received"))
    
    # Send verification complete message
    await message.answer(
        get_text(language, "verification_complete"),
        parse_mode="Markdown"
    )
    
    # Send verification documents to operator
    if operator_telegram_id:
        try:
            # Header message
            await bot.send_message(
                chat_id=operator_telegram_id,
                text=f"🔐 **{get_text(language, 'verification_docs')}**\n\n"
                     f"👤 От: {respondent_info}",
                parse_mode="Markdown"
            )
            
            # Send passport photo
            if passport_photo_id:
                await bot.send_photo(
                    chat_id=operator_telegram_id,
                    photo=passport_photo_id,
                    caption=f"📸 {get_text(language, 'passport_photo_caption')}\n👤 {respondent_info}"
                )
            
            # Send selfie video note
            await bot.send_video_note(
                chat_id=operator_telegram_id,
                video_note=selfie_video_id
            )
            await bot.send_message(
                chat_id=operator_telegram_id,
                text=f"🎥 {get_text(language, 'passport_selfie_caption')}\n👤 {respondent_info}"
            )
            
        except Exception as e:
            print(f"Error sending verification docs to operator: {e}")
    
    # Clear state - verification complete
    await state.clear()


@router.message(QuestionnaireStates.waiting_passport_selfie)
async def waiting_passport_selfie_invalid(message: Message, state: FSMContext):
    """Handle non-video messages when waiting for selfie video."""
    data = await state.get_data()
    language = data.get('language', 'en')
    await message.answer(get_text(language, "waiting_video"))
