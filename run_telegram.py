"""
Main entry point for the HealthyBot Telegram service.
Switched to synchronous pyTelegramBotAPI (telebot).
"""

import logging
import sys
import telebot
from telebot.types import Message

import config
from database.models import init_db
from telegram_bot.handlers.message_handler import handle_message, handle_callback
from telegram_bot.handlers.onboarding import (
    start as start_onboarding,
    get_gender_callback,
    get_goal_callback,
    get_diet_callback,
    confirm_callback
)
from telegram_bot.scheduler import setup_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main():
    logger.info("🚀 Starting HealthyBot Telegram (Sync Mode)...")

    # 1. Initialize DB
    init_db()

    # 2. Initialize Bot
    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        logger.error("❌ TELEGRAM_BOT_TOKEN not set in .env")
        return

    bot = telebot.TeleBot(config.TELEGRAM_BOT_TOKEN)

    # 3. Setup Scheduler (runs in background thread)
    setup_scheduler(bot)

    # 4. Register Handlers
    
    @bot.message_handler(commands=['start'])
    def cmd_start(message: Message):
        start_onboarding(bot, message)

    @bot.message_handler(commands=['help'])
    def cmd_help(message: Message):
        help_text = (
            "👋 **HealthyBot Help**\n\n"
            "I'm your health coach. You can talk to me naturally or use commands:\n"
            "/start - Setup your profile\n"
            "/help - See this message\n\n"
            "**Examples of what you can say:**\n"
            "• \"Log 2 rotis and subji for lunch\"\n"
            "• \"I walked for 45 minutes\"\n"
            "• \"Show my summary for today\"\n"
            "• \"How much water did I drink?\"\n\n"
            "Just talk to me like a friend! 😊"
        )
        bot.reply_to(message, help_text, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: True)
    def callback_router(call: telebot.types.CallbackQuery):
        # Route callbacks based on data prefix
        data = call.data
        if data.startswith("gender_"):
            get_gender_callback(bot, call)
        elif data.startswith("goal_"):
            get_goal_callback(bot, call)
        elif data.startswith("diet_"):
            get_diet_callback(bot, call)
        elif data.startswith("confirm_"):
            confirm_callback(bot, call)
        else:
            handle_callback(bot, call)

    @bot.message_handler(func=lambda message: True)
    def text_handler(message: Message):
        handle_message(bot, message)

    # 5. Start Polling
    logger.info("✅ Bot is online and polling...")
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Bot polling crashed: {e}")


if __name__ == "__main__":
    main()
