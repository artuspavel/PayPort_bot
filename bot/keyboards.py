"""Keyboard builders for the bot."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_menu() -> InlineKeyboardMarkup:
    """Admin main menu keyboard."""
    builder = InlineKeyboardBuilder()
    # Operator functions (admin can also use them)
    builder.row(
        InlineKeyboardButton(text="🔗 Создать ссылку-приглашение", callback_data="operator:create_invite")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Мои приглашения", callback_data="operator:my_invites")
    )
    builder.row(
        InlineKeyboardButton(text="📄 Все анкеты", callback_data="operator:all_questionnaires")
    )
    # Admin functions
    builder.row(
        InlineKeyboardButton(text="➕ Добавить оператора", callback_data="admin:add_operator")
    )
    builder.row(
        InlineKeyboardButton(text="➖ Удалить оператора", callback_data="admin:remove_operator")
    )
    builder.row(
        InlineKeyboardButton(text="👑 Назначить админа", callback_data="admin:make_admin")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Снять статус админа", callback_data="admin:demote_admin")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin:list_operators")
    )
    builder.row(
        InlineKeyboardButton(text="📝 Редактировать вопросы", callback_data="admin:edit_questions")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 В начало", callback_data="main:start")
    )
    return builder.as_markup()


def operator_menu() -> InlineKeyboardMarkup:
    """Operator main menu keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔗 Создать ссылку-приглашение", callback_data="operator:create_invite")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Мои приглашения", callback_data="operator:my_invites")
    )
    builder.row(
        InlineKeyboardButton(text="📄 Все анкеты", callback_data="operator:all_questionnaires")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 В начало", callback_data="main:start")
    )
    return builder.as_markup()


def invite_created_keyboard(invite_link: str) -> InlineKeyboardMarkup:
    """Keyboard shown after invite creation with copy button."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📋 Копировать ссылку",
            copy_text=CopyTextButton(text=invite_link)
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔗 Создать ещё", callback_data="operator:create_invite")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Мои приглашения", callback_data="operator:my_invites")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 В начало", callback_data="main:start")
    )
    return builder.as_markup()


def cancel_button() -> InlineKeyboardMarkup:
    """Cancel button."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Confirmation keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=f"confirm:{action}"),
        InlineKeyboardButton(text="❌ Нет", callback_data="cancel")
    )
    return builder.as_markup()


def questions_menu_keyboard() -> InlineKeyboardMarkup:
    """Questions management menu."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Редактировать вопрос", callback_data="questions:edit_list")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Добавить вопрос", callback_data="questions:add")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить вопрос", callback_data="questions:delete_list")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад в меню", callback_data="admin:menu")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 В начало", callback_data="main:start")
    )
    return builder.as_markup()


def questions_list_keyboard(questions: list, action: str = "edit") -> InlineKeyboardMarkup:
    """Questions list for editing or deleting."""
    builder = InlineKeyboardBuilder()
    for q in questions:
        # Truncate long questions for button text
        short_text = q['text'][:35] + "..." if len(q['text']) > 35 else q['text']
        icon = "✏️" if action == "edit" else "🗑"
        builder.row(
            InlineKeyboardButton(
                text=f"{icon} {short_text}",
                callback_data=f"{action}_q:{q['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:edit_questions"),
        InlineKeyboardButton(text="🏠 В начало", callback_data="main:start")
    )
    return builder.as_markup()


def operators_list_keyboard(operators: list, action: str = "remove") -> InlineKeyboardMarkup:
    """Operators list keyboard."""
    builder = InlineKeyboardBuilder()
    for op in operators:
        status = "👑" if op['is_admin'] else "👤"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} @{op['username']}",
                callback_data=f"{action}_op:{op['username']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:menu"),
        InlineKeyboardButton(text="🏠 В начало", callback_data="main:start")
    )
    return builder.as_markup()


def skip_description_keyboard() -> InlineKeyboardMarkup:
    """Skip description button for invite creation."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏭ Пропустить описание", callback_data="skip_description")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def language_selection_keyboard() -> InlineKeyboardMarkup:
    """Language selection for questionnaire."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")
    )
    builder.row(
        InlineKeyboardButton(text="🇸🇦 العربية", callback_data="lang:ar")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def invites_list_keyboard(invites: list) -> InlineKeyboardMarkup:
    """List of invites with clickable buttons to view questionnaires."""
    builder = InlineKeyboardBuilder()
    for inv in invites[:15]:  # Limit to 15
        desc = inv['description'][:20] if inv['description'] else inv['invite_code'][:10]
        lang = inv.get('language', 'en')
        lang_flag = "🇷🇺" if lang == "ru" else "🇬🇧"
        completed = inv['completed_count']
        icon = "✅" if completed > 0 else "⏳"
        builder.row(
            InlineKeyboardButton(
                text=f"{lang_flag} {desc} - {icon} {completed}",
                callback_data=f"invite:{inv['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔗 Создать новое", callback_data="operator:create_invite")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 В начало", callback_data="main:start")
    )
    return builder.as_markup()


def invite_detail_keyboard(invite_id: int, questionnaires: list) -> InlineKeyboardMarkup:
    """Detail view of invite with list of questionnaires."""
    builder = InlineKeyboardBuilder()
    
    for q in questionnaires[:10]:  # Limit to 10
        name = q.get('respondent_name', 'Unknown')[:15]
        username = q.get('respondent_username', '')
        if username:
            name = f"@{username}"[:15]
        
        status = q.get('status', '')
        if status == 'completed':
            icon = "✅"
            # Add button to download
            builder.row(
                InlineKeyboardButton(
                    text=f"{icon} {name}",
                    callback_data=f"download_q:{q['id']}"
                )
            )
        elif status == 'in_progress':
            icon = "⏳"
            builder.row(
                InlineKeyboardButton(
                    text=f"{icon} {name} (в процессе)",
                    callback_data=f"q_info:{q['id']}"
                )
            )
        else:
            icon = "❌"
            builder.row(
                InlineKeyboardButton(
                    text=f"{icon} {name} (отменено)",
                    callback_data=f"q_info:{q['id']}"
                )
            )
    
    if not questionnaires:
        builder.row(
            InlineKeyboardButton(text="📭 Анкет пока нет", callback_data="noop")
        )
    
    builder.row(
        InlineKeyboardButton(text="🔙 К списку приглашений", callback_data="operator:my_invites")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 В начало", callback_data="main:start")
    )
    return builder.as_markup()


def back_to_invite_keyboard(invite_id: int) -> InlineKeyboardMarkup:
    """Back to invite detail keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"invite:{invite_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 В начало", callback_data="main:start")
    )
    return builder.as_markup()


def all_questionnaires_keyboard(questionnaires: list, page: int = 0, page_size: int = 10, show_operator: bool = False) -> InlineKeyboardMarkup:
    """List of all questionnaires with pagination.
    
    Args:
        questionnaires: List of questionnaire dicts
        page: Current page number (0-based)
        page_size: Items per page
        show_operator: If True, show operator username (for admin view)
    """
    builder = InlineKeyboardBuilder()
    
    # Calculate pagination
    total = len(questionnaires)
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, total)
    page_items = questionnaires[start_idx:end_idx]
    
    for q in page_items:
        # Build display name
        username = q.get('respondent_username', '')
        if username:
            name = f"@{username}"[:12]
        else:
            name = q.get('respondent_name', 'Unknown')[:12]
        
        # For admin view: show operator username
        if show_operator:
            op_username = q.get('operator_username', '')
            if op_username:
                name = f"{name} 👤{op_username[:8]}"
        else:
            # Add invite description for context
            invite_desc = q.get('invite_description', '')[:10]
            if invite_desc:
                name = f"{name} ({invite_desc})"
        
        status = q.get('status', '')
        if status == 'completed':
            icon = "✅"
            builder.row(
                InlineKeyboardButton(
                    text=f"{icon} {name}",
                    callback_data=f"download_q:{q['id']}"
                )
            )
        elif status == 'in_progress':
            icon = "⏳"
            builder.row(
                InlineKeyboardButton(
                    text=f"{icon} {name} (в процессе)",
                    callback_data=f"q_info:{q['id']}"
                )
            )
        else:
            icon = "❌"
            builder.row(
                InlineKeyboardButton(
                    text=f"{icon} {name} (отменено)",
                    callback_data=f"q_info:{q['id']}"
                )
            )
    
    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"all_q_page:{page - 1}")
        )
    if end_idx < total:
        nav_buttons.append(
            InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"all_q_page:{page + 1}")
        )
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Filter buttons
    builder.row(
        InlineKeyboardButton(text="✅ Только заполненные", callback_data="all_q_filter:completed"),
        InlineKeyboardButton(text="📋 Все", callback_data="all_q_filter:all")
    )
    
    # Operator filter button (only for admin view)
    if show_operator:
        builder.row(
            InlineKeyboardButton(text="👤 Фильтр по оператору", callback_data="all_q_filter:by_operator")
        )
    
    builder.row(
        InlineKeyboardButton(text="🏠 В начало", callback_data="main:start")
    )
    return builder.as_markup()


def operators_filter_keyboard(operators: list) -> InlineKeyboardMarkup:
    """Keyboard for filtering questionnaires by operator (admin only).
    
    Args:
        operators: List of operator dicts with 'id', 'username', 'completed', 'total'
    """
    builder = InlineKeyboardBuilder()
    
    # Show all operators button
    builder.row(
        InlineKeyboardButton(text="📋 Все операторы", callback_data="all_q_operator:all")
    )
    
    for op in operators[:15]:  # Limit to 15
        username = op.get('username', 'unknown')
        completed = op.get('completed', 0)
        total = op.get('total', 0)
        builder.row(
            InlineKeyboardButton(
                text=f"👤 @{username} — ✅{completed}/{total}",
                callback_data=f"all_q_operator:{op['id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Назад к анкетам", callback_data="operator:all_questionnaires")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 В начало", callback_data="main:start")
    )
    return builder.as_markup()
