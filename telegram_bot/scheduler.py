"""
Scheduler — automated daily reminders via Telegram.
Uses the synchronous 'schedule' library.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

import schedule
import telebot

from core.agent import run as run_agent, get_user_context
from core.llm_client import GroqClient
from database import crud
from utils.helpers import now_local

logger = logging.getLogger(__name__)


def _get_all_users() -> list[dict]:
    """Get all onboarded users (sync)."""
    import sqlite3
    from config import DB_PATH
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cursor = db.execute(
            "SELECT * FROM users WHERE onboarding_done = 1"
        )
        return [dict(r) for r in cursor.fetchall()]


# ──────────────────────────────────────────────────────────────────
# Job callbacks (Synchronous)
# ──────────────────────────────────────────────────────────────────

def morning_ping(bot: telebot.TeleBot) -> None:
    """Send morning motivation + today's plan."""
    users = _get_all_users()

    for user in users:
        try:
            profile_ctx = get_user_context(user["id"])
            stats = crud.get_weekly_stats(user["id"])

            prompt = (
                f"You are a friendly health coach. Generate a brief good-morning message for:\n"
                f"User Profile: {profile_ctx}\nGoal: {user.get('goal', 'maintain')}\n"
                f"Stats this week: {stats['avg_cal']} cal/day, {stats['workouts_completed']} workouts.\n"
                f"Instructions: 1) Warm greeting 2) 1-line health tip/focus based on profile 3) Motivational closer.\n"
                f"Persona: Supportive Indian friend. Language: English with casual tone. Max 4 sentences."
            )

            client = GroqClient()
            message = client.chat(messages=[{"role": "user", "content": prompt}], preset="coach")

            from telegram_bot.keyboards import morning_keyboard
            bot.send_message(
                chat_id=user["telegram_id"],
                text=message,
                reply_markup=morning_keyboard(),
            )
        except Exception as e:
            logger.error(f"Morning ping failed for user {user['id']}: {e}")


def meal_reminder(bot: telebot.TeleBot) -> None:
    """Send meal logging reminder (no LLM — saves API budget)."""
    users = _get_all_users()
    hour = now_local().hour

    if hour < 14:
        meal = "lunch 🍽️"
    else:
        meal = "dinner 🍽️"

    for user in users:
        try:
            bot.send_message(
                chat_id=user["telegram_id"],
                text=f"Hey {user.get('name', 'there')}! Had {meal} yet?\n"
                     f"Just tell me what you ate and I'll track the macros for you! 📊",
            )
        except Exception as e:
            logger.error(f"Meal reminder failed for user {user['id']}: {e}")


def evening_summary(bot: telebot.TeleBot) -> None:
    """Send end-of-day summary with LLM insights + dashboard image."""
    users = _get_all_users()

    for user in users:
        try:
            history = crud.get_chat_history(user["id"], limit=20)
            response = run_agent(user["id"], "Give me today's summary with calorie totals", history)
            
            bot.send_message(
                chat_id=user["telegram_id"],
                text=f"🌙 **End of Day Summary**\n\n{response}",
                parse_mode="Markdown",
            )

            # Send dashboard image
            try:
                from telegram_bot.dashboard_image import generate_dashboard_image
                img_path = generate_dashboard_image(user["id"], days=1)
                with open(img_path, "rb") as photo:
                    bot.send_photo(
                        chat_id=user["telegram_id"],
                        photo=photo,
                        caption="📊 Today's Dashboard"
                    )
            except Exception as img_err:
                logger.error(f"Dashboard image failed for user {user['id']}: {img_err}")

        except Exception as e:
            logger.error(f"Evening summary failed for user {user['id']}: {e}")


def weekly_review(bot: telebot.TeleBot) -> None:
    """Send weekly review on Sundays."""
    users = _get_all_users()

    for user in users:
        try:
            history = crud.get_chat_history(user["id"], limit=20)
            response = run_agent(user["id"], "Evaluate my progress for the last 7 days", history)
            
            bot.send_message(
                chat_id=user["telegram_id"],
                text=f"📊 **Weekly Review**\n\n{response}",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Weekly review failed for user {user['id']}: {e}")


# ──────────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────────

def setup_scheduler(bot: telebot.TeleBot) -> None:
    """Register all scheduled jobs using the 'schedule' library."""
    
    # Morning ping — 7:00 AM IST
    schedule.every().day.at("07:00").do(morning_ping, bot=bot)

    # Lunch reminder — 1:40 PM IST (temporarily set for testing)
    schedule.every().day.at("13:40").do(meal_reminder, bot=bot)

    # Dinner reminder — 7:30 PM IST
    schedule.every().day.at("19:30").do(meal_reminder, bot=bot)

    # Evening summary — 10:00 PM IST
    schedule.every().day.at("22:00").do(evening_summary, bot=bot)

    # Weekly review — Sunday 9:00 PM IST
    schedule.every().sunday.at("21:00").do(weekly_review, bot=bot)

    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)

    # Start scheduler in a background thread
    daemon = threading.Thread(target=run_scheduler, daemon=True)
    daemon.start()

    logger.info("✅ Sync Scheduler started: morning ping, meal reminders, evening summary, weekly review")
