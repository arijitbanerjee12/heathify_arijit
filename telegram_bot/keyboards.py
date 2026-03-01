"""
Telegram inline keyboard builders.
Uses pyTelegramBotAPI (telebot) types.
"""

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


def goal_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔥 Lose Fat", callback_data="goal_fat_loss"))
    markup.add(InlineKeyboardButton("💪 Gain Muscle", callback_data="goal_muscle_gain"))
    markup.add(InlineKeyboardButton("⚖️ Maintain", callback_data="goal_maintain"))
    return markup


def gender_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("♂️ Male", callback_data="gender_male"),
        InlineKeyboardButton("♀️ Female", callback_data="gender_female"),
    )
    markup.add(InlineKeyboardButton("🏳️ Prefer not to say", callback_data="gender_other"))
    return markup


def diet_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🥬 Vegetarian", callback_data="diet_veg"))
    markup.add(InlineKeyboardButton("🥚 Eggetarian", callback_data="diet_egg"))
    markup.add(InlineKeyboardButton("🍗 Non-Vegetarian", callback_data="diet_nonveg"))
    markup.add(InlineKeyboardButton("🌱 Vegan", callback_data="diet_vegan"))
    return markup


def workout_complete_keyboard(workout_id: int) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Done", callback_data=f"workout_done_{workout_id}"),
        InlineKeyboardButton("🔄 Partial", callback_data=f"workout_partial_{workout_id}"),
        InlineKeyboardButton("❌ Skipped", callback_data=f"workout_skip_{workout_id}"),
    )
    return markup


def morning_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("💪 Let's go!", callback_data="morning_go"),
        InlineKeyboardButton("😴 Skip today", callback_data="morning_skip"),
    )
    return markup


def confirm_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Confirm", callback_data="confirm_yes"),
        InlineKeyboardButton("🔄 Redo", callback_data="confirm_no"),
    )
    return markup
