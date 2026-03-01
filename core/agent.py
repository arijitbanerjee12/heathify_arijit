"""
LLM Agent — the brain of HealthyBot.
Uses Groq's native tool/function calling to decide actions.
Fully synchronous — works in Streamlit without any async.
"""

import json
import os
from typing import Optional

from groq import Groq

import config
from core.tools import TOOL_DEFINITIONS, execute_tool


# ──────────────────────────────────────────────────────────────────
# System prompt — defines the agent's persona and behavior
# ──────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are HealthyBot — a warm, caring Indian health buddy.
You talk like a supportive friend who happens to know about fitness and nutrition.
You help track meals, exercise, and habits. You give personalized advice based on data.

RULES:
- Talk like a FRIEND, not a textbook. Be warm, casual, genuine.
- Keep responses short — 2-4 natural sentences. NO bullet point lists unless asked.
- Use Indian food/fitness context (roti, dal, paneer, etc.).
- Use emojis sparingly (1-2 max per message).
- NEVER start with "Hey!" or "Great question!" — just respond naturally.
- When user reports food they ate → call log_meal with accurate nutrition estimates.
- When user reports exercise → call log_exercise.
- When user reports sleep/screen/water/junk → call log_habits.
- When user asks about past data → call get_day_summary or get_date_range_data.
- When user asks about progress → call evaluate_progress.
- When user asks for suggestions → call suggest_workout or suggest_meal.
- When user asks for a visual dashboard, chart, stats image, or "show me my dashboard" → call generate_dashboard.
- When user wants to change their plan → call update_plan.
- When user shares a preference worth remembering → call save_user_preference.
- When user asks to DELETE a duplicate/wrong entry → first call get_day_summary to find entry IDs, then call delete_entry with the correct entry_id. ALWAYS use the tool — never say you can't delete.
- For greetings, questions, or casual chat → just respond directly, NO tool call.
- After a tool returns data, craft a natural, friendly response around it.
- Use common Indian food nutrition knowledge (roti ~120kcal, dal ~150kcal/bowl, rice ~130kcal/100g, etc.)

IMPORTANT: Only call log_meal when the user describes food they ALREADY ATE.
Questions like "is it too late for dinner?" or "I haven't eaten yet" are NOT meal logs.

{user_context}"""


def _get_client() -> Groq:
    """Get or create Groq client."""
    return Groq(api_key=config.GROQ_API_KEY)


def _load_user_summary() -> str:
    """Load persistent user preferences/summary."""
    path = os.path.join("data", "user_summary.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            return f"\nUser's saved preferences:\n{content}\n"
    return ""


def get_user_context(user_id: int) -> str:
    """Build user context string from DB profile + saved preferences."""
    import sqlite3
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return ""

    user = dict(row)
    profile = (
        f"\nUser profile: {user.get('name', 'User')}, {user.get('age', '?')}y, "
        f"{user.get('gender', '?')}, {user.get('height_cm', '?')}cm, "
        f"{user.get('weight_kg', '?')}kg\n"
        f"Goal: {user.get('goal', 'maintain')}\n"
        f"Diet: {user.get('dietary_prefs', 'any')}\n"
        f"Wake: {user.get('wake_time', '07:00')}, Sleep: {user.get('sleep_time', '23:00')}"
    )

    prefs = _load_user_summary()
    return profile + prefs


def run(user_id: int, message: str, chat_history: list[dict] = None) -> str:
    """
    Main entry point. Send a message, get a response.

    Args:
        user_id: Database user ID
        message: User's message text
        chat_history: List of {"role": "user"|"assistant", "content": "..."} dicts

    Returns:
        Bot's response string
    """
    if chat_history is None:
        chat_history = []

    # Build messages array
    user_context = get_user_context(user_id)
    system_msg = SYSTEM_PROMPT.format(user_context=user_context)

    messages = [{"role": "system", "content": system_msg}]

    # Add recent chat history (last 20 messages for context/memory)
    for msg in chat_history[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current message
    messages.append({"role": "user", "content": message})

    # Call Groq with tools
    client = _get_client()

    try:
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.7,
            max_completion_tokens=1024,
        )
    except Exception as e:
        return f"Sorry, I'm having trouble connecting right now. Error: {str(e)}"

    reply = response.choices[0].message

    # Check if LLM wants to call a tool
    if reply.tool_calls:
        # Execute each tool call
        tool_results = []
        for tool_call in reply.tool_calls:
            fn_name = tool_call.function.name
            try:
                fn_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            result = execute_tool(fn_name, fn_args, user_id)
            tool_results.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": fn_name,
                "content": result,
            })

        # Send tool results back to LLM for final response
        followup_messages = messages + [
            {"role": "assistant", "content": reply.content or "", "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in reply.tool_calls
            ]},
        ] + tool_results

        # Check if any tool result had a dashboard image marker
        image_prefix = ""
        for tr in tool_results:
            content = tr.get("content", "")
            for line in content.split("\n"):
                if line.startswith("DASHBOARD_IMAGE:"):
                    image_prefix = line + "\n"
                    break

        try:
            final_response = client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=followup_messages,
                temperature=0.7,
                max_completion_tokens=1024,
            )
            final_text = final_response.choices[0].message.content or "Done! ✅"
            return image_prefix + final_text
        except Exception as e:
            # If second call fails, return the tool result directly
            return tool_results[0]["content"] if tool_results else f"Error: {str(e)}"

    # No tool call — direct response
    return reply.content or "I'm here! How can I help? 😊"
