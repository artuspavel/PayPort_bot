"""Translation service for converting Arabic answers to English."""
import asyncio
from functools import lru_cache
from typing import Optional

# NOTE: Using deep-translator with Google Translate (free, no API key needed)
# If rate limited, consider switching to paid API
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False


def translate_text(text: str, source_lang: str = 'ar', target_lang: str = 'en') -> str:
    """Translate text from source language to target language.
    
    Args:
        text: Text to translate
        source_lang: Source language code (e.g., 'ar' for Arabic)
        target_lang: Target language code (e.g., 'en' for English)
    
    Returns:
        Translated text, or original if translation fails
    """
    if not TRANSLATOR_AVAILABLE:
        return text
    
    if not text or not text.strip():
        return text
    
    # Skip if text is mostly non-translatable (numbers, symbols, usernames)
    if _is_non_translatable(text):
        return text
    
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        translated = translator.translate(text)
        return translated if translated else text
    except Exception as e:
        # Log error but return original text
        print(f"Translation error: {e}")
        return text


async def translate_text_async(text: str, source_lang: str = 'ar', target_lang: str = 'en') -> str:
    """Async wrapper for translate_text."""
    # Run sync translation in thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, translate_text, text, source_lang, target_lang)


def translate_answers(answers: dict, source_lang: str = 'ar', target_lang: str = 'en') -> dict:
    """Translate all answers in a dictionary.
    
    Args:
        answers: Dict of {question_key: answer_text}
        source_lang: Source language code
        target_lang: Target language code
    
    Returns:
        Dict with translated answers
    """
    if not TRANSLATOR_AVAILABLE:
        return answers
    
    translated = {}
    for key, value in answers.items():
        if isinstance(value, str):
            translated[key] = translate_text(value, source_lang, target_lang)
        else:
            translated[key] = value
    
    return translated


async def translate_answers_async(answers: dict, source_lang: str = 'ar', target_lang: str = 'en') -> dict:
    """Async version of translate_answers."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, translate_answers, answers, source_lang, target_lang)


def _is_non_translatable(text: str) -> bool:
    """Check if text is mostly non-translatable (numbers, symbols, usernames).
    
    Returns True if text should be skipped for translation.
    """
    # Remove whitespace for analysis
    stripped = text.strip()
    
    # Very short text
    if len(stripped) < 3:
        return True
    
    # Starts with @ (username)
    if stripped.startswith('@'):
        return True
    
    # Mostly numbers and symbols
    alpha_count = sum(1 for c in stripped if c.isalpha())
    if alpha_count < len(stripped) * 0.3:  # Less than 30% letters
        return True
    
    return False
