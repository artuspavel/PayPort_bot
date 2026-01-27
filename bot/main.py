"""
PayPort Questionnaire Telegram Bot
Main entry point
"""
import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from bot.config import BOT_TOKEN, QUESTIONS_FILE, FINGERPRINT_SERVER_PORT
from bot import database as db
from bot.handlers import common, admin, operator, questionnaire
from bot.fingerprint_server import create_fingerprint_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Actions on bot startup."""
    logger.info("Initializing database...")
    await db.init_db()
    
    # Load questions from JSON if DB is empty
    questions = await db.get_all_questions()
    if not questions:
        logger.info("Loading questions from JSON file...")
        await db.load_questions_from_json(QUESTIONS_FILE)
    
    # Get bot info
    bot_info = await bot.get_me()
    logger.info(f"Bot started: @{bot_info.username}")


async def run_fingerprint_server():
    """Run fingerprint collection web server."""
    app = create_fingerprint_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', FINGERPRINT_SERVER_PORT)
    await site.start()
    logger.info(f"Fingerprint server started on port {FINGERPRINT_SERVER_PORT}")
    return runner


async def main():
    """Main function to run the bot."""
    # Initialize bot and dispatcher
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    
    # Register routers
    # NOTE: Order matters! More specific handlers should be registered first
    dp.include_router(questionnaire.router)  # Questionnaire FSM handler
    dp.include_router(admin.router)
    dp.include_router(operator.router)
    dp.include_router(common.router)  # Common handlers last (includes /start)
    
    # Register startup hook
    dp.startup.register(on_startup)
    
    # Start fingerprint server
    fp_runner = await run_fingerprint_server()
    
    # Start polling
    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await fp_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

