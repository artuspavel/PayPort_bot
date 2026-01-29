"""Database service for the bot."""
import aiosqlite
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

from bot.config import DATABASE_PATH, FIRST_ADMIN_USERNAME


async def init_db():
    """Initialize the database with required tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Users table (operators and admins)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT NOT NULL UNIQUE,
                is_admin INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Invites table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS invites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operator_id INTEGER NOT NULL,
                invite_code TEXT UNIQUE NOT NULL,
                description TEXT,
                language TEXT DEFAULT 'en',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (operator_id) REFERENCES users(id)
            )
        """)
        
        # Migration: add language column if not exists
        try:
            await db.execute("ALTER TABLE invites ADD COLUMN language TEXT DEFAULT 'en'")
        except:
            pass  # Column already exists
        
        # Questionnaires table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS questionnaires (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invite_id INTEGER NOT NULL,
                respondent_telegram_id INTEGER NOT NULL,
                respondent_username TEXT,
                respondent_name TEXT,
                answers_json TEXT,
                status TEXT DEFAULT 'in_progress',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                FOREIGN KEY (invite_id) REFERENCES invites(id)
            )
        """)
        
        # Questions table (editable by admin)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_num INTEGER NOT NULL,
                text TEXT NOT NULL,
                key TEXT NOT NULL UNIQUE,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Fingerprints table for fraud detection
        await db.execute("""
            CREATE TABLE IF NOT EXISTS fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                questionnaire_id INTEGER,
                ip_address TEXT,
                user_agent TEXT,
                screen_resolution TEXT,
                timezone TEXT,
                language TEXT,
                platform TEXT,
                canvas_hash TEXT,
                webgl_hash TEXT,
                fonts_hash TEXT,
                is_premium INTEGER DEFAULT 0,
                raw_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (questionnaire_id) REFERENCES questionnaires(id)
            )
        """)

        # Pending verifications (user must complete fingerprint before questionnaire)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_verifications (
                telegram_id INTEGER PRIMARY KEY,
                invite_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (invite_id) REFERENCES invites(id)
            )
        """)
        
        await db.commit()
        
        # Add first admin if not exists
        await add_first_admin()


async def add_first_admin():
    """Add the first admin user if not exists."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM users WHERE username = ?",
            (FIRST_ADMIN_USERNAME.lower(),)
        )
        if not await cursor.fetchone():
            await db.execute(
                "INSERT INTO users (username, is_admin) VALUES (?, 1)",
                (FIRST_ADMIN_USERNAME.lower(),)
            )
            await db.commit()


async def load_questions_from_json(json_path: Path):
    """Load questions from JSON file into database.
    
    NOTE: Questions now have text_ru, text_en, and text_ar fields.
    We store them as JSON in the text field for flexibility.
    """
    if not json_path.exists():
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        for q in questions:
            # Store all languages as JSON
            text_data = json.dumps({
                "ru": q.get('text_ru', q.get('text', '')),
                "en": q.get('text_en', q.get('text', '')),
                "ar": q.get('text_ar', q.get('text_en', ''))  # Fallback to English if no Arabic
            }, ensure_ascii=False)
            
            await db.execute("""
                INSERT INTO questions (order_num, text, key, is_active)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(key) DO UPDATE SET
                    order_num = excluded.order_num,
                    text = excluded.text
            """, (q['id'], text_data, q['key']))
        await db.commit()


# ============ User Management ============

async def get_user_by_username(username: str) -> Optional[dict]:
    """Get user by username."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username.lower().lstrip('@'),)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def save_pending_verification(telegram_id: int, invite_id: int):
    """Save or update pending verification for a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO pending_verifications (telegram_id, invite_id)
            VALUES (?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                invite_id = excluded.invite_id,
                created_at = CURRENT_TIMESTAMP
        """, (telegram_id, invite_id))
        await db.commit()


async def get_pending_verification(telegram_id: int) -> Optional[dict]:
    """Get pending verification for a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM pending_verifications WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def clear_pending_verification(telegram_id: int):
    """Clear pending verification for a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM pending_verifications WHERE telegram_id = ?",
            (telegram_id,),
        )
        await db.commit()


async def get_user_by_telegram_id(telegram_id: int) -> Optional[dict]:
    """Get user by Telegram ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ? AND is_active = 1",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_user_telegram_id(username: str, telegram_id: int):
    """Update user's Telegram ID when they first interact with bot."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET telegram_id = ? WHERE username = ?",
            (telegram_id, username.lower().lstrip('@'))
        )
        await db.commit()


async def add_operator(username: str, added_by_admin_id: int) -> bool:
    """Add new operator."""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO users (username, is_admin) VALUES (?, 0)",
                (username.lower().lstrip('@'),)
            )
            await db.commit()
            return True
    except aiosqlite.IntegrityError:
        return False


async def remove_operator(username: str) -> bool:
    """Deactivate operator."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "UPDATE users SET is_active = 0 WHERE username = ? AND is_admin = 0",
            (username.lower().lstrip('@'),)
        )
        await db.commit()
        return cursor.rowcount > 0


async def make_admin(username: str) -> bool:
    """Promote user to admin."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "UPDATE users SET is_admin = 1 WHERE username = ? AND is_active = 1",
            (username.lower().lstrip('@'),)
        )
        await db.commit()
        return cursor.rowcount > 0


async def demote_admin(username: str) -> bool:
    """Demote admin to regular operator."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "UPDATE users SET is_admin = 0 WHERE username = ? AND is_active = 1",
            (username.lower().lstrip('@'),)
        )
        await db.commit()
        return cursor.rowcount > 0


async def list_operators() -> list:
    """List all active operators."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE is_active = 1 ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ============ Invite Management ============

async def create_invite(operator_id: int, description: str = None, language: str = "en") -> str:
    """Create new invite code with language preference."""
    invite_code = secrets.token_urlsafe(8)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO invites (operator_id, invite_code, description, language) VALUES (?, ?, ?, ?)",
            (operator_id, invite_code, description, language)
        )
        await db.commit()
    return invite_code


async def get_invite_by_code(invite_code: str) -> Optional[dict]:
    """Get invite by code."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT i.*, u.username as operator_username, u.telegram_id as operator_telegram_id
               FROM invites i 
               JOIN users u ON i.operator_id = u.id
               WHERE i.invite_code = ?""",
            (invite_code,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def list_operator_invites(operator_id: int) -> list:
    """List all invites created by operator."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT i.*, 
                      (SELECT COUNT(*) FROM questionnaires q WHERE q.invite_id = i.id AND q.status = 'completed') as completed_count
               FROM invites i 
               WHERE i.operator_id = ?
               ORDER BY i.created_at DESC""",
            (operator_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ============ Questionnaire Management ============

async def start_questionnaire(invite_id: int, respondent_telegram_id: int, 
                              respondent_username: str, respondent_name: str) -> int:
    """Start new questionnaire session."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO questionnaires 
               (invite_id, respondent_telegram_id, respondent_username, respondent_name, answers_json, status)
               VALUES (?, ?, ?, ?, '{}', 'in_progress')""",
            (invite_id, respondent_telegram_id, respondent_username, respondent_name)
        )
        await db.commit()
        return cursor.lastrowid


async def get_active_questionnaire(respondent_telegram_id: int) -> Optional[dict]:
    """Get active questionnaire for respondent."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT q.*, i.operator_id, u.telegram_id as operator_telegram_id, u.username as operator_username
               FROM questionnaires q
               JOIN invites i ON q.invite_id = i.id
               JOIN users u ON i.operator_id = u.id
               WHERE q.respondent_telegram_id = ? AND q.status = 'in_progress'
               ORDER BY q.created_at DESC LIMIT 1""",
            (respondent_telegram_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def save_answer(questionnaire_id: int, question_key: str, answer: str):
    """Save answer to questionnaire."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get current answers
        cursor = await db.execute(
            "SELECT answers_json FROM questionnaires WHERE id = ?",
            (questionnaire_id,)
        )
        row = await cursor.fetchone()
        answers = json.loads(row[0]) if row and row[0] else {}
        
        # Add new answer
        answers[question_key] = answer
        
        # Update
        await db.execute(
            "UPDATE questionnaires SET answers_json = ? WHERE id = ?",
            (json.dumps(answers, ensure_ascii=False), questionnaire_id)
        )
        await db.commit()


async def cancel_questionnaire(respondent_telegram_id: int) -> bool:
    """Cancel incomplete questionnaire for respondent."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "UPDATE questionnaires SET status = 'cancelled' WHERE respondent_telegram_id = ? AND status = 'in_progress'",
            (respondent_telegram_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def complete_questionnaire(questionnaire_id: int) -> dict:
    """Mark questionnaire as completed and return full data."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE questionnaires SET status = 'completed', completed_at = ? WHERE id = ?",
            (datetime.now().isoformat(), questionnaire_id)
        )
        await db.commit()
        
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT q.*, i.operator_id, i.description as invite_description, i.language,
                      u.telegram_id as operator_telegram_id, u.username as operator_username
               FROM questionnaires q
               JOIN invites i ON q.invite_id = i.id
               JOIN users u ON i.operator_id = u.id
               WHERE q.id = ?""",
            (questionnaire_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else {}


# ============ Questions Management ============

async def get_all_questions() -> list:
    """Get all active questions ordered."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM questions WHERE is_active = 1 ORDER BY order_num"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def update_question(question_id: int, new_text: str) -> bool:
    """Update question text."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "UPDATE questions SET text = ? WHERE id = ?",
            (new_text, question_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def add_question(order_num: int, text: str, key: str) -> bool:
    """Add new question."""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO questions (order_num, text, key) VALUES (?, ?, ?)",
                (order_num, text, key)
            )
            await db.commit()
            return True
    except aiosqlite.IntegrityError:
        return False


async def delete_question(question_id: int) -> bool:
    """Soft delete question."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "UPDATE questions SET is_active = 0 WHERE id = ?",
            (question_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


# ============ Questionnaire Archive ============

async def get_questionnaires_by_invite(invite_id: int) -> list:
    """Get all questionnaires for an invite."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT q.*, i.language, i.description as invite_description
               FROM questionnaires q
               JOIN invites i ON q.invite_id = i.id
               WHERE q.invite_id = ?
               ORDER BY q.created_at DESC""",
            (invite_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_questionnaire_by_id(questionnaire_id: int) -> Optional[dict]:
    """Get questionnaire by ID with full data."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT q.*, i.operator_id, i.description as invite_description, i.language,
                      u.telegram_id as operator_telegram_id, u.username as operator_username
               FROM questionnaires q
               JOIN invites i ON q.invite_id = i.id
               JOIN users u ON i.operator_id = u.id
               WHERE q.id = ?""",
            (questionnaire_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_invite_by_id(invite_id: int) -> Optional[dict]:
    """Get invite by ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT i.*, u.username as operator_username, u.telegram_id as operator_telegram_id
               FROM invites i 
               JOIN users u ON i.operator_id = u.id
               WHERE i.id = ?""",
            (invite_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_incomplete_questionnaire_for_invite(respondent_telegram_id: int, invite_id: int) -> Optional[dict]:
    """Get incomplete questionnaire for specific invite and respondent.
    
    NOTE: This allows resuming questionnaire from where user left off.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT q.*, i.language, i.description as invite_description
               FROM questionnaires q
               JOIN invites i ON q.invite_id = i.id
               WHERE q.respondent_telegram_id = ? 
                 AND q.invite_id = ?
                 AND q.status = 'in_progress'
               ORDER BY q.created_at DESC LIMIT 1""",
            (respondent_telegram_id, invite_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_questionnaire_answers(questionnaire_id: int) -> dict:
    """Get answers dict for questionnaire."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT answers_json FROM questionnaires WHERE id = ?",
            (questionnaire_id,)
        )
        row = await cursor.fetchone()
        return json.loads(row[0]) if row and row[0] else {}


async def get_all_operator_questionnaires(operator_id: int, status_filter: str = None) -> list:
    """Get all questionnaires for operator across all invites.
    
    Args:
        operator_id: Database ID of the operator
        status_filter: Optional filter - 'completed', 'in_progress', 'cancelled'
    
    Returns:
        List of questionnaires with invite info, ordered by date desc
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        query = """
            SELECT q.*, i.description as invite_description, i.language, i.invite_code,
                   u.username as operator_username
            FROM questionnaires q
            JOIN invites i ON q.invite_id = i.id
            JOIN users u ON i.operator_id = u.id
            WHERE i.operator_id = ?
        """
        params = [operator_id]
        
        if status_filter:
            query += " AND q.status = ?"
            params.append(status_filter)
        
        query += " ORDER BY q.created_at DESC"
        
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def count_operator_questionnaires(operator_id: int) -> dict:
    """Count questionnaires by status for operator.
    
    Returns:
        Dict with counts: {'completed': N, 'in_progress': N, 'cancelled': N, 'total': N}
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT q.status, COUNT(*) as cnt
            FROM questionnaires q
            JOIN invites i ON q.invite_id = i.id
            WHERE i.operator_id = ?
            GROUP BY q.status
        """, (operator_id,))
        
        rows = await cursor.fetchall()
        
        counts = {'completed': 0, 'in_progress': 0, 'cancelled': 0, 'total': 0}
        for row in rows:
            status, cnt = row
            if status in counts:
                counts[status] = cnt
            counts['total'] += cnt
        
        return counts


async def get_all_questionnaires_admin(status_filter: str = None) -> list:
    """Get ALL questionnaires in the system (for admin).
    
    Args:
        status_filter: Optional filter - 'completed', 'in_progress', 'cancelled'
    
    Returns:
        List of all questionnaires with operator info, ordered by date desc
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        query = """
            SELECT q.*, i.description as invite_description, i.language, i.invite_code,
                   u.username as operator_username
            FROM questionnaires q
            JOIN invites i ON q.invite_id = i.id
            JOIN users u ON i.operator_id = u.id
        """
        params = []
        
        if status_filter:
            query += " WHERE q.status = ?"
            params.append(status_filter)
        
        query += " ORDER BY q.created_at DESC"
        
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def count_all_questionnaires_admin() -> dict:
    """Count ALL questionnaires by status (for admin).
    
    Returns:
        Dict with counts: {'completed': N, 'in_progress': N, 'cancelled': N, 'total': N}
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT status, COUNT(*) as cnt
            FROM questionnaires
            GROUP BY status
        """)
        
        rows = await cursor.fetchall()
        
        counts = {'completed': 0, 'in_progress': 0, 'cancelled': 0, 'total': 0}
        for row in rows:
            status, cnt = row
            if status in counts:
                counts[status] = cnt
            counts['total'] += cnt
        
        return counts


async def get_operators_with_questionnaire_counts() -> list:
    """Get list of operators with their questionnaire counts (for admin filter).
    
    Returns:
        List of dicts: [{'id': N, 'username': 'xxx', 'completed': N, 'total': N}, ...]
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT 
                u.id,
                u.username,
                COUNT(q.id) as total,
                SUM(CASE WHEN q.status = 'completed' THEN 1 ELSE 0 END) as completed
            FROM users u
            LEFT JOIN invites i ON i.operator_id = u.id
            LEFT JOIN questionnaires q ON q.invite_id = i.id
            WHERE u.is_active = 1
            GROUP BY u.id, u.username
            HAVING total > 0
            ORDER BY total DESC
        """)
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ============ Fingerprint Management ============

async def save_fingerprint(telegram_id: int, fingerprint_data: dict, questionnaire_id: int = None) -> int:
    """Save fingerprint data for a user.
    
    Args:
        telegram_id: User's Telegram ID
        fingerprint_data: Dict with fingerprint fields
        questionnaire_id: Optional linked questionnaire
    
    Returns:
        ID of saved fingerprint record
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO fingerprints (
                telegram_id, questionnaire_id, ip_address, user_agent,
                screen_resolution, timezone, language, platform,
                canvas_hash, webgl_hash, fonts_hash, is_premium, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            telegram_id,
            questionnaire_id,
            fingerprint_data.get('ip_address'),
            fingerprint_data.get('user_agent'),
            fingerprint_data.get('screen_resolution'),
            fingerprint_data.get('timezone'),
            fingerprint_data.get('language'),
            fingerprint_data.get('platform'),
            fingerprint_data.get('canvas_hash'),
            fingerprint_data.get('webgl_hash'),
            fingerprint_data.get('fonts_hash'),
            fingerprint_data.get('is_premium', 0),
            json.dumps(fingerprint_data, ensure_ascii=False)
        ))
        await db.commit()
        return cursor.lastrowid


async def find_matching_fingerprints(fingerprint_data: dict, exclude_telegram_id: int = None) -> list:
    """Find fingerprints that match the given data.
    
    Checks for matches on: IP, canvas_hash, screen+timezone combo
    
    Returns:
        List of matching fingerprints with questionnaire info
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        matches = []
        
        # Match by IP address (if not empty/localhost)
        ip = fingerprint_data.get('ip_address')
        if ip and ip not in ('127.0.0.1', '::1', None, ''):
            query = """
                SELECT DISTINCT f.*, q.respondent_username, q.respondent_name, q.status as q_status,
                       i.description as invite_description
                FROM fingerprints f
                LEFT JOIN questionnaires q ON f.questionnaire_id = q.id
                LEFT JOIN invites i ON q.invite_id = i.id
                WHERE f.ip_address = ?
            """
            params = [ip]
            if exclude_telegram_id:
                query += " AND f.telegram_id != ?"
                params.append(exclude_telegram_id)
            
            cursor = await db.execute(query, params)
            for row in await cursor.fetchall():
                match = dict(row)
                match['match_type'] = 'ip_address'
                matches.append(match)
        
        # Match by canvas hash (strong indicator)
        canvas = fingerprint_data.get('canvas_hash')
        if canvas and canvas not in (None, '', 'error'):
            query = """
                SELECT DISTINCT f.*, q.respondent_username, q.respondent_name, q.status as q_status,
                       i.description as invite_description
                FROM fingerprints f
                LEFT JOIN questionnaires q ON f.questionnaire_id = q.id
                LEFT JOIN invites i ON q.invite_id = i.id
                WHERE f.canvas_hash = ?
            """
            params = [canvas]
            if exclude_telegram_id:
                query += " AND f.telegram_id != ?"
                params.append(exclude_telegram_id)
            
            cursor = await db.execute(query, params)
            for row in await cursor.fetchall():
                match = dict(row)
                match['match_type'] = 'canvas_hash'
                if match not in matches:
                    matches.append(match)
        
        # Match by screen + timezone + platform combo
        screen = fingerprint_data.get('screen_resolution')
        tz = fingerprint_data.get('timezone')
        platform = fingerprint_data.get('platform')
        if screen and tz and platform:
            query = """
                SELECT DISTINCT f.*, q.respondent_username, q.respondent_name, q.status as q_status,
                       i.description as invite_description
                FROM fingerprints f
                LEFT JOIN questionnaires q ON f.questionnaire_id = q.id
                LEFT JOIN invites i ON q.invite_id = i.id
                WHERE f.screen_resolution = ? AND f.timezone = ? AND f.platform = ?
            """
            params = [screen, tz, platform]
            if exclude_telegram_id:
                query += " AND f.telegram_id != ?"
                params.append(exclude_telegram_id)
            
            cursor = await db.execute(query, params)
            for row in await cursor.fetchall():
                match = dict(row)
                match['match_type'] = 'device_combo'
                if match not in matches:
                    matches.append(match)
        
        return matches


async def link_fingerprint_to_questionnaire(fingerprint_id: int, questionnaire_id: int):
    """Link a fingerprint record to a questionnaire."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE fingerprints SET questionnaire_id = ? WHERE id = ?",
            (questionnaire_id, fingerprint_id)
        )
        await db.commit()


async def get_fingerprint_by_telegram_id(telegram_id: int) -> Optional[dict]:
    """Get most recent fingerprint for a telegram user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM fingerprints WHERE telegram_id = ? ORDER BY created_at DESC LIMIT 1",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_fingerprint_by_id(fingerprint_id: int) -> Optional[dict]:
    """Get fingerprint by ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM fingerprints WHERE id = ?",
            (fingerprint_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

