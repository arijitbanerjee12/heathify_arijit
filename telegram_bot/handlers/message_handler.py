"""
Main message handler for Telegram.
Routes all natural language messages through the LLM Agent.
Uses pyTelegramBotAPI (telebot).
"""

import logging
import telebot
from telebot.types import Message

from core.agent import run as run_agent
from database import crud

logger = logging.getLogger(__name__)


def handle_message(bot: telebot.TeleBot, message: Message):
    """Handle natural language messages from the user."""
    telegram_id = message.from_user.id
    user_text = message.text

    # Skip if no text
    if not user_text:
        return

    # 1. Identify/Create user
    user = crud.get_user_by_telegram_id(telegram_id)
    if not user:
        # Should normally be handled by onboarding, but safety first
        crud.create_user(telegram_id, message.from_user.first_name)
        user = crud.get_user_by_telegram_id(telegram_id)

    user_id = user["id"]

    # 2. Get chat history for context
    history = crud.get_chat_history(user_id, limit=10)

    # 3. Inform user we're thinking (simulated)
    bot.send_chat_action(message.chat.id, 'typing')

    try:
        # 4. Run Agent (Synchronous)
        response_text = run_agent(user_id, user_text, history)

        # 5. Save history
        crud.save_chat_message(user_id, "user", user_text)
        crud.save_chat_message(user_id, "assistant", response_text)

        # 6. Check for dashboard image
        if "DASHBOARD_IMAGE:" in response_text:
            _send_dashboard_image(bot, message, response_text)
        else:
            # 7. Send text response
            try:
                bot.reply_to(message, response_text, parse_mode="Markdown")
            except Exception as markdown_err:
                logger.warning(f"Markdown parsing failed, falling back to plain text: {markdown_err}")
                bot.reply_to(message, response_text)

    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        bot.reply_to(message, "Ouch, something went wrong while processing that. Mind trying again? 😅")


def _send_dashboard_image(bot: telebot.TeleBot, message: Message, response_text: str):
    """Extract dashboard image path from response and send as photo."""
    import os
    lines = response_text.split("\n")
    image_path = None
    text_lines = []

    for line in lines:
        if line.startswith("DASHBOARD_IMAGE:"):
            image_path = line.replace("DASHBOARD_IMAGE:", "").strip()
        else:
            text_lines.append(line)

    clean_text = "\n".join(text_lines).strip()

    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, "rb") as photo:
                bot.send_photo(message.chat.id, photo, caption="📊 Here's your dashboard!")
        except Exception as e:
            logger.error(f"Failed to send dashboard image: {e}")
            bot.reply_to(message, "Sorry, I couldn't send the dashboard image. 😅")

    if clean_text:
        try:
            bot.reply_to(message, clean_text, parse_mode="Markdown")
        except Exception:
            bot.reply_to(message, clean_text)



def handle_callback(bot: telebot.TeleBot, call: telebot.types.CallbackQuery):
    """Handle button clicks."""
    telegram_id = call.from_user.id
    user = crud.get_user_by_telegram_id(telegram_id)
    
    if not user:
        bot.answer_callback_query(call.id, "Please start with /start first!")
        return

    # Delegate complex callbacks to specific handlers if needed
    # For now, handle simple ones or show notification
    data = call.data
    
    if data.startswith("workout_done_"):
        wid = int(data.replace("workout_done_", ""))
        crud.update_workout_completion(wid, True)
        bot.answer_callback_query(call.id, "Workout marked as completed! 🎉")
        bot.edit_message_text("Great job finishing that workout! 💪", call.message.chat.id, call.message.message_id)
        
    elif data.startswith("morning_"):
        if data == "morning_go":
            bot.answer_callback_query(call.id, "Let's crush it! 🔥")
        else:
            bot.answer_callback_query(call.id, "Rest is important too. 😴")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    
    else:
        bot.answer_callback_query(call.id, "Understood! ✅")
