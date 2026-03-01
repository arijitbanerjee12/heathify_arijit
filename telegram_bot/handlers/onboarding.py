"""
Onboarding flow for Telegram (/start command).
Uses pyTelegramBotAPI (telebot) with register_next_step_handler.
"""

import telebot
from telebot.types import Message
from database import crud
from telegram_bot.keyboards import goal_keyboard, gender_keyboard, diet_keyboard, confirm_keyboard

# Temporary storage for onboarding data
ONBOARDING_DATA = {}


def start(bot: telebot.TeleBot, message: Message):
    """Entry point — /start command."""
    user = crud.get_user_by_telegram_id(message.from_user.id)

    if user and user.get("onboarding_done"):
        bot.send_message(
            message.chat.id,
            f"Welcome back, {user['name']}! 👋\n\n"
            "Just send me a message and I'll figure out what you need. For example:\n"
            "• \"I had 2 rotis and dal for lunch\"\n"
            "• \"Did 30 min running\"\n"
            "• \"What did I eat today?\"\n\n"
            "I'm your health coach — talk to me naturally! 💬"
        )
        return

    # Create user record
    crud.create_user(message.from_user.id)
    ONBOARDING_DATA[message.from_user.id] = {}

    bot.send_message(
        message.chat.id,
        "🌟 **Welcome to HealthyBot!** 🌟\n\n"
        "Let's set up your profile. It'll take just a minute!\n\n"
        "**What's your name?**",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(message, get_name, bot)


def get_name(message: Message, bot: telebot.TeleBot):
    name = message.text.strip()
    ONBOARDING_DATA[message.from_user.id]["name"] = name

    bot.send_message(
        message.chat.id,
        f"Nice to meet you, {name}! 🙌\n\n**How old are you?**",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(message, get_age, bot)


def get_age(message: Message, bot: telebot.TeleBot):
    try:
        ageInt = int(message.text.strip())
        if ageInt < 10 or ageInt > 120:
            raise ValueError()
    except ValueError:
        bot.send_message(message.chat.id, "Please enter a valid age (10-120).")
        bot.register_next_step_handler(message, get_age, bot)
        return

    ONBOARDING_DATA[message.from_user.id]["age"] = ageInt
    bot.send_message(
        message.chat.id,
        "**What's your gender?**",
        reply_markup=gender_keyboard(),
        parse_mode="Markdown"
    )
    # GENDER is handled via callback, so we don't register_next_step here


def get_gender_callback(bot: telebot.TeleBot, call: telebot.types.CallbackQuery):
    gender = call.data.replace("gender_", "")
    ONBOARDING_DATA[call.from_user.id]["gender"] = gender

    bot.edit_message_text(
        f"Got it! ✅\n\n"
        f"**What's your height (cm) and weight (kg)?**\n"
        f"(e.g., `170 75`)",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(call.message, get_height_weight, bot)


def get_height_weight(message: Message, bot: telebot.TeleBot):
    import re
    numbers = re.findall(r"[\d.]+", message.text.strip())

    if len(numbers) < 2:
        bot.send_message(message.chat.id, "Please enter both height and weight. Example: `170 75`")
        bot.register_next_step_handler(message, get_height_weight, bot)
        return

    height = float(numbers[0])
    weight = float(numbers[1])

    if height > 250: height, weight = weight, height
    if height < 100 or height > 250 or weight < 20 or weight > 250:
        bot.send_message(message.chat.id, "Please enter realistic values (H: 100-250, W: 20-250).")
        bot.register_next_step_handler(message, get_height_weight, bot)
        return

    ONBOARDING_DATA[message.from_user.id]["height_cm"] = height
    ONBOARDING_DATA[message.from_user.id]["weight_kg"] = weight

    bot.send_message(
        message.chat.id,
        "**What's your main goal?**",
        reply_markup=goal_keyboard(),
        parse_mode="Markdown"
    )


def get_goal_callback(bot: telebot.TeleBot, call: telebot.types.CallbackQuery):
    goal = call.data.replace("goal_", "")
    ONBOARDING_DATA[call.from_user.id]["goal"] = goal

    bot.edit_message_text(
        "**What's your dietary preference?**",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=diet_keyboard(),
        parse_mode="Markdown"
    )


def get_diet_callback(bot: telebot.TeleBot, call: telebot.types.CallbackQuery):
    diet = call.data.replace("diet_", "")
    ONBOARDING_DATA[call.from_user.id]["dietary_prefs"] = diet

    bot.edit_message_text(
        "**Almost done!** ⏰\n\nWhen do you wake up and sleep? (e.g., `7:00 23:00`)",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(call.message, get_wake_sleep, bot)


def get_wake_sleep(message: Message, bot: telebot.TeleBot):
    import re
    times = re.findall(r"(\d{1,2}(?::\d{2})?)\s*(?:am|pm)?", message.text.strip().lower())
    if len(times) < 2:
        bot.send_message(message.chat.id, "Please enter both times. Example: `7:00 23:00`")
        bot.register_next_step_handler(message, get_wake_sleep, bot)
        return

    wake = times[0] if ":" in times[0] else f"{times[0]}:00"
    sleep = times[1] if ":" in times[1] else f"{times[1]}:00"

    data = ONBOARDING_DATA[message.from_user.id]
    data["wake_time"] = wake
    data["sleep_time"] = sleep

    summary = (
        f"📋 **Your Profile:**\n\n"
        f"👤 {data.get('name')}\n"
        f"📅 {data.get('age')} years, {data.get('gender', '').title()}\n"
        f"📏 {data.get('height_cm')} cm, {data.get('weight_kg')} kg\n"
        f"🎯 {data.get('goal', '').replace('_', ' ').title()}\n"
        f"🥗 {data.get('dietary_prefs', '').title()}\n"
        f"⏰ Wake: {wake} | Sleep: {sleep}\n\n"
        f"**Does this look right?**"
    )

    bot.send_message(message.chat.id, summary, reply_markup=confirm_keyboard(), parse_mode="Markdown")


def confirm_callback(bot: telebot.TeleBot, call: telebot.types.CallbackQuery):
    if call.data == "confirm_no":
        bot.send_message(call.message.chat.id, "Let's start over. **What's your name?**", parse_mode="Markdown")
        bot.register_next_step_handler(call.message, get_name, bot)
        return

    data = ONBOARDING_DATA.get(call.from_user.id, {})
    crud.update_user(
        call.from_user.id,
        name=data.get("name", ""),
        age=data.get("age"),
        gender=data.get("gender", ""),
        height_cm=data.get("height_cm"),
        weight_kg=data.get("weight_kg"),
        goal=data.get("goal", "maintain"),
        dietary_prefs=data.get("dietary_prefs", ""),
        wake_time=data.get("wake_time", "07:00"),
        sleep_time=data.get("sleep_time", "23:00"),
        onboarding_done=1
    )

    bot.edit_message_text(
        "✅ **Profile saved!** Welcome aboard! 🎉\n\n"
        "Talk to me naturally to log food, exercise, or habits. 💪",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="Markdown"
    )
    if call.from_user.id in ONBOARDING_DATA:
        del ONBOARDING_DATA[call.from_user.id]
