"""
Tools the LLM agent can call.
Each tool is a plain sync function that takes structured args and returns a result string.
The LLM fills the args via Groq's native function calling.
"""

import json
import sqlite3
from datetime import date, datetime, timedelta
from typing import Optional

from config import DB_PATH
from utils.helpers import format_macros, now_local


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _today():
    return date.today().isoformat()


def _resolve_date(date_str: str) -> str:
    """Resolve natural date references to ISO format."""
    s = date_str.strip().lower()
    today = date.today()

    if s in ("today", ""):
        return today.isoformat()
    if s == "yesterday":
        return (today - timedelta(days=1)).isoformat()
    if s == "day before yesterday":
        return (today - timedelta(days=2)).isoformat()

    # Day names: "last monday", "monday", etc.
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, day_name in enumerate(day_names):
        if day_name in s:
            current_weekday = today.weekday()
            days_ago = (current_weekday - i) % 7
            if days_ago == 0:
                days_ago = 7  # "monday" means last monday
            return (today - timedelta(days=days_ago)).isoformat()

    # Try parsing as ISO date
    try:
        return datetime.strptime(s, "%Y-%m-%d").date().isoformat()
    except ValueError:
        pass

    # Try DD/MM/YYYY
    try:
        return datetime.strptime(s, "%d/%m/%Y").date().isoformat()
    except ValueError:
        pass

    return today.isoformat()


# ──────────────────────────────────────────────────────────────────
# TOOL DEFINITIONS (JSON schemas for Groq function calling)
# ──────────────────────────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "log_meal",
            "description": "Log a meal the user has eaten. Call this when the user reports food they ALREADY ATE. You MUST estimate realistic nutrition values for each food item based on your knowledge. Use typical Indian serving sizes. Be accurate — these values will be stored and tracked.",
            "parameters": {
                "type": "object",
                "properties": {
                    "meal_type": {
                        "type": "string",
                        "enum": ["breakfast", "lunch", "dinner", "snack"],
                        "description": "Type of meal"
                    },
                    "items": {
                        "type": "array",
                        "description": "List of food items eaten with ACCURATE nutrition estimates",
                        "items": {
                            "type": "object",
                            "properties": {
                                "food_name": {"type": "string", "description": "Name of the food item (e.g. 'Steamed White Rice', 'Aloo Posto')"},
                                "serving_size": {"type": "string", "description": "Serving description (e.g. '1 cup cooked, ~200g', '2 pieces')"},
                                "quantity_g": {"type": "number", "description": "Total quantity in grams"},
                                "cal": {"type": "number", "description": "Calories (kcal) — use realistic values"},
                                "protein_g": {"type": "number", "description": "Protein in grams"},
                                "carb_g": {"type": "number", "description": "Carbohydrates in grams"},
                                "fat_g": {"type": "number", "description": "Fat in grams"},
                                "fiber_g": {"type": "number", "description": "Fiber in grams"}
                            },
                            "required": ["food_name", "quantity_g", "cal", "protein_g", "carb_g", "fat_g"]
                        }
                    },
                    "raw_text": {"type": "string", "description": "Original meal description from user"}
                },
                "required": ["meal_type", "items", "raw_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_exercise",
            "description": "Log exercise/workout the user has done. Call when user reports physical activity they completed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "exercise_type": {
                        "type": "string",
                        "enum": ["strength", "cardio", "yoga", "sports", "mixed", "other"],
                        "description": "Type of exercise"
                    },
                    "exercises": {"type": "string", "description": "Description of exercises done"},
                    "duration_min": {"type": "integer", "description": "Duration in minutes"},
                    "intensity": {
                        "type": "string",
                        "enum": ["low", "moderate", "high"],
                        "description": "Intensity level"
                    }
                },
                "required": ["exercise_type", "exercises", "duration_min", "intensity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_habits",
            "description": "Log daily habits: sleep, screen time, water intake, junk food. Call when user reports any of these.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sleep_hours": {"type": "number", "description": "Hours of sleep (0 if not mentioned)"},
                    "screen_time_min": {"type": "integer", "description": "Screen time in minutes (0 if not mentioned)"},
                    "water_glasses": {"type": "integer", "description": "Glasses of water (0 if not mentioned)"},
                    "junk_desc": {"type": "string", "description": "Description of junk food eaten (empty if none)"},
                    "junk_cal": {"type": "number", "description": "Estimated junk food calories (0 if none)"}
                },
                "required": ["sleep_hours", "screen_time_min", "water_glasses"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_day_summary",
            "description": "Get meals, exercise, and habits for a specific day. Use for questions like 'what did I eat today/yesterday', 'did I exercise on Monday', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date to query. Can be: 'today', 'yesterday', 'monday', 'tuesday', or ISO date like '2026-02-28'"
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_date_range_data",
            "description": "Get data across a date range. Use for 'last week', 'past 3 days', 'this month' type queries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_back": {
                        "type": "integer",
                        "description": "Number of days to look back"
                    },
                    "data_type": {
                        "type": "string",
                        "enum": ["meals", "exercise", "habits", "all"],
                        "description": "What type of data to fetch"
                    }
                },
                "required": ["days_back", "data_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_progress",
            "description": "Evaluate the user's health progress. Call when user asks 'am I doing good?', 'how is my progress?', 'am I on track?'",
            "parameters": {
                "type": "object",
                "properties": {
                    "period_days": {
                        "type": "integer",
                        "description": "Number of days to evaluate (default 14)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_workout",
            "description": "Suggest a workout. Call when user asks for exercise ideas or workout plans.",
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "enum": ["upper", "lower", "core", "full_body", "cardio", "any"],
                        "description": "Optional focus area. Use 'any' if not specific."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_meal",
            "description": "Suggest a meal. Call when user asks what to eat or needs meal ideas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "meal_type": {
                        "type": "string",
                        "enum": ["breakfast", "lunch", "dinner", "snack", "any"],
                        "description": "Which meal to suggest. Use 'any' if not specific."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_plan",
            "description": "Update user's health plan/profile. Call when user wants to change goal, diet, weight, or other profile settings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "enum": ["goal", "weight_kg", "dietary_prefs", "wake_time", "sleep_time"],
                        "description": "Which field to update"
                    },
                    "value": {
                        "type": "string",
                        "description": "New value for the field"
                    }
                },
                "required": ["field", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_user_preference",
            "description": "Save an important user preference or personal detail for future reference. Call when user shares likes/dislikes, dietary restrictions, injuries, routines, or any information worth remembering.",
            "parameters": {
                "type": "object",
                "properties": {
                    "note": {
                        "type": "string",
                        "description": "The preference or detail to remember, e.g. 'Doesn't like paneer', 'Has knee pain', 'Prefers Bengali food'"
                    }
                },
                "required": ["note"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_entry",
            "description": "Delete a logged meal, exercise, or habit entry. Use when user asks to remove a duplicate or incorrect entry. Use get_day_summary first to find the entry ID if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entry_type": {
                        "type": "string",
                        "enum": ["meal", "exercise", "habit"],
                        "description": "Type of entry to delete"
                    },
                    "entry_id": {
                        "type": "integer",
                        "description": "The database ID of the entry to delete"
                    }
                },
                "required": ["entry_type", "entry_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_dashboard",
            "description": "Generate a visual dashboard infographic image. Call when user asks to 'show dashboard', 'show my stats', 'visual summary', 'how does my week look', 'send me a chart', or any request for a visual/graphical view of their health data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to include. 1 = today only, 7 = last week, 30 = last month. Default 1."
                    }
                },
                "required": []
            }
        }
    },
]


# ──────────────────────────────────────────────────────────────────
# TOOL EXECUTORS (called by the agent when LLM makes a tool call)
# ──────────────────────────────────────────────────────────────────

def execute_tool(tool_name: str, args: dict, user_id: int) -> str:
    """Route a tool call to the right executor. Returns result string."""
    executors = {
        "log_meal": _exec_log_meal,
        "log_exercise": _exec_log_exercise,
        "log_habits": _exec_log_habits,
        "get_day_summary": _exec_get_day_summary,
        "get_date_range_data": _exec_get_date_range,
        "evaluate_progress": _exec_evaluate_progress,
        "suggest_workout": _exec_suggest_workout,
        "suggest_meal": _exec_suggest_meal,
        "update_plan": _exec_update_plan,
        "save_user_preference": _exec_save_preference,
        "delete_entry": _exec_delete_entry,
        "generate_dashboard": _exec_generate_dashboard,
    }

    executor = executors.get(tool_name)
    if not executor:
        return f"Unknown tool: {tool_name}"

    try:
        return executor(args, user_id)
    except Exception as e:
        return f"Tool error: {str(e)}"


def _exec_log_meal(args: dict, user_id: int) -> str:
    items = args.get("items", [])
    meal_type = args.get("meal_type", "other")
    raw_text = args.get("raw_text", "")

    # Use LLM-provided nutrition values directly (no local DB lookup needed)
    total_cal = sum(i.get("cal", 0) for i in items)
    total_protein = sum(i.get("protein_g", 0) for i in items)
    total_carb = sum(i.get("carb_g", 0) for i in items)
    total_fat = sum(i.get("fat_g", 0) for i in items)

    # Store
    conn = _connect()
    cursor = conn.execute(
        "INSERT INTO meals (user_id, date, meal_type, raw_text, total_cal, protein_g, carb_g, fat_g) VALUES (?,?,?,?,?,?,?,?)",
        (user_id, _today(), meal_type, raw_text, total_cal, total_protein, total_carb, total_fat),
    )
    meal_id = cursor.lastrowid
    for item in items:
        conn.execute(
            "INSERT INTO meal_items (meal_id, food_name, quantity_g, cal, protein_g, carb_g, fat_g) VALUES (?,?,?,?,?,?,?)",
            (meal_id, item.get("food_name", ""), item.get("quantity_g", 0),
             item.get("cal", 0), item.get("protein_g", 0), item.get("carb_g", 0), item.get("fat_g", 0)),
        )
    conn.commit()
    conn.close()

    item_lines = ", ".join(
        f"{i['food_name']} ({i.get('serving_size', '')} — {i.get('cal', 0):.0f} kcal, {i.get('protein_g', 0):.0f}g protein)"
        for i in items
    )
    return (
        f"MEAL LOGGED SUCCESSFULLY: {meal_type}\n"
        f"Items: {item_lines}\n"
        f"Total: {total_cal:.0f} kcal, {total_protein:.0f}g protein, "
        f"{total_carb:.0f}g carbs, {total_fat:.0f}g fat"
    )


def _exec_log_exercise(args: dict, user_id: int) -> str:
    conn = _connect()
    conn.execute(
        "INSERT INTO workouts (user_id, date, type, duration_min, intensity, planned, notes) VALUES (?,?,?,?,?,?,?)",
        (user_id, _today(), args.get("exercise_type", "other"),
         args.get("duration_min", 0), args.get("intensity", "moderate"),
         args.get("exercises", ""), args.get("exercises", "")),
    )
    conn.commit()
    conn.close()
    return (
        f"EXERCISE LOGGED: {args.get('exercises', 'workout')} | "
        f"{args.get('duration_min', 0)} min | {args.get('intensity', 'moderate')} intensity"
    )


def _exec_log_habits(args: dict, user_id: int) -> str:
    sleep = args.get("sleep_hours", 0)
    screen = args.get("screen_time_min", 0)
    water = args.get("water_glasses", 0)
    junk_desc = args.get("junk_desc", "")
    junk_cal = args.get("junk_cal", 0)

    conn = _connect()
    conn.execute(
        "INSERT INTO habits (user_id, date, screen_time_min, junk_desc, junk_cal, sleep_hours, water_glasses, notes) VALUES (?,?,?,?,?,?,?,?)",
        (user_id, _today(), screen, junk_desc, junk_cal, sleep, water, ""),
    )
    conn.commit()
    conn.close()

    # Compute score
    score = 50
    if 7 <= sleep <= 9: score += 20
    elif 6 <= sleep < 7: score += 10
    elif sleep < 5: score -= 10
    if screen <= 60: score += 15
    elif screen <= 120: score += 5
    elif screen > 240: score -= 10
    if water >= 8: score += 15
    elif water >= 5: score += 5
    elif water < 3: score -= 5
    if junk_cal == 0: score += 10
    elif junk_cal > 500: score -= 15
    score = max(0, min(100, score))

    return (
        f"HABITS LOGGED: Sleep {sleep}h, Screen {screen}min, Water {water} glasses, "
        f"Junk: {junk_desc or 'none'} ({junk_cal} kcal) | Habit Score: {score}/100"
    )


def _exec_get_day_summary(args: dict, user_id: int) -> str:
    target_date = _resolve_date(args.get("date", "today"))

    conn = _connect()

    # Meals
    meals = [dict(r) for r in conn.execute(
        "SELECT * FROM meals WHERE user_id=? AND date=? ORDER BY created_at", (user_id, target_date)
    ).fetchall()]

    # Workouts
    workouts = [dict(r) for r in conn.execute(
        "SELECT * FROM workouts WHERE user_id=? AND date=?", (user_id, target_date)
    ).fetchall()]

    # Habits (Aggregate for the day)
    habit_rows = conn.execute(
        "SELECT * FROM habits WHERE user_id=? AND date=?", (user_id, target_date)
    ).fetchall()
    
    habits = None
    if habit_rows:
        # Sum water, take max for others
        total_water = sum(r["water_glasses"] for r in habit_rows)
        max_sleep = max(r["sleep_hours"] for r in habit_rows)
        max_screen = max(r["screen_time_min"] for r in habit_rows)
        all_junk = " | ".join(set(r["junk_desc"] for r in habit_rows if r["junk_desc"]))
        
        habits = {
            "sleep_hours": max_sleep,
            "screen_time_min": max_screen,
            "water_glasses": total_water,
            "junk_desc": all_junk
        }

    conn.close()

    parts = [f"DATA FOR {target_date}:"]

    if meals:
        total_cal = sum(m["total_cal"] for m in meals)
        total_pro = sum(m["protein_g"] for m in meals)
        meal_descs = [f"[id={m['id']}] {m['meal_type']}: {m['raw_text']} ({m['total_cal']:.0f} kcal)" for m in meals]
        parts.append(f"MEALS ({len(meals)}): " + " | ".join(meal_descs))
        parts.append(f"TOTAL: {total_cal:.0f} kcal, {total_pro:.0f}g protein")
    else:
        parts.append("MEALS: None logged")

    if workouts:
        w_descs = [f"[id={w['id']}] {w['type']} {w['duration_min']}min ({w['intensity']})" for w in workouts]
        parts.append(f"EXERCISE: " + " | ".join(w_descs))
    else:
        parts.append("EXERCISE: None logged")

    if habits:
        parts.append(f"HABITS: Sleep {habits['sleep_hours']}h, Screen {habits['screen_time_min']}min, Water {habits['water_glasses']} glasses")
        if habits["junk_desc"]:
            parts.append(f"JUNK: {habits['junk_desc']}")
    else:
        parts.append("HABITS: Not logged")

    return "\n".join(parts)


def _exec_get_date_range(args: dict, user_id: int) -> str:
    days = args.get("days_back", 7)
    data_type = args.get("data_type", "all")
    start_date = (date.today() - timedelta(days=days)).isoformat()

    conn = _connect()
    parts = [f"DATA FOR LAST {days} DAYS (since {start_date}):"]

    if data_type in ("meals", "all"):
        meals = [dict(r) for r in conn.execute(
            "SELECT date, meal_type, raw_text, total_cal, protein_g FROM meals WHERE user_id=? AND date>=? ORDER BY date",
            (user_id, start_date),
        ).fetchall()]
        if meals:
            cal_by_date = {}
            for m in meals:
                cal_by_date.setdefault(m["date"], 0)
                cal_by_date[m["date"]] += m["total_cal"]
            for d, cal in sorted(cal_by_date.items()):
                parts.append(f"  {d}: {cal:.0f} kcal")
        else:
            parts.append("  No meals logged")

    if data_type in ("exercise", "all"):
        workouts = [dict(r) for r in conn.execute(
            "SELECT date, type, duration_min, intensity, completed FROM workouts WHERE user_id=? AND date>=? ORDER BY date",
            (user_id, start_date),
        ).fetchall()]
        if workouts:
            parts.append(f"EXERCISE ({len(workouts)} sessions):")
            for w in workouts:
                parts.append(f"  {w['date']}: {w['type']} {w['duration_min']}min ({w['intensity']})")
        else:
            parts.append("  No exercise logged")

    if data_type in ("habits", "all"):
        habits = [dict(r) for r in conn.execute(
            "SELECT date, sleep_hours, screen_time_min, water_glasses FROM habits WHERE user_id=? AND date>=? ORDER BY date",
            (user_id, start_date),
        ).fetchall()]
        if habits:
            avg_sleep = sum(h["sleep_hours"] for h in habits) / len(habits)
            parts.append(f"HABITS ({len(habits)} days): Avg sleep {avg_sleep:.1f}h")
        else:
            parts.append("  No habits logged")

    conn.close()
    return "\n".join(parts)


def _exec_evaluate_progress(args: dict, user_id: int) -> str:
    days = args.get("period_days", 14)
    start = (date.today() - timedelta(days=days)).isoformat()
    mid = (date.today() - timedelta(days=days // 2)).isoformat()

    conn = _connect()

    # Get user profile
    user_row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    user = dict(user_row) if user_row else {}

    # First half vs second half comparison
    meals_first = conn.execute(
        "SELECT total_cal, protein_g FROM meals WHERE user_id=? AND date>=? AND date<?", (user_id, start, mid)
    ).fetchall()
    meals_second = conn.execute(
        "SELECT total_cal, protein_g FROM meals WHERE user_id=? AND date>=?", (user_id, mid)
    ).fetchall()

    workouts_first = conn.execute("SELECT * FROM workouts WHERE user_id=? AND date>=? AND date<?", (user_id, start, mid)).fetchall()
    workouts_second = conn.execute("SELECT * FROM workouts WHERE user_id=? AND date>=?", (user_id, mid)).fetchall()

    conn.close()

    goal = user.get("goal", "maintain")
    target_cal = {"fat_loss": 1600, "muscle_gain": 2500, "maintain": 2000}.get(goal, 2000)

    def _avg_cal(rows):
        if not rows:
            return 0
        total = sum(r["total_cal"] for r in rows)
        days_count = len(set(r["total_cal"] for r in rows)) or 1  # rough
        return total / max(len(rows), 1)

    avg_cal_1 = _avg_cal(meals_first) if meals_first else 0
    avg_cal_2 = _avg_cal(meals_second) if meals_second else 0

    return (
        f"PROGRESS EVALUATION (last {days} days):\n"
        f"Goal: {goal} (target ~{target_cal} kcal/day)\n"
        f"First {days//2} days: avg {avg_cal_1:.0f} kcal/meal, {len(workouts_first)} workouts\n"
        f"Last {days//2} days: avg {avg_cal_2:.0f} kcal/meal, {len(workouts_second)} workouts\n"
        f"Total meals logged: {len(meals_first) + len(meals_second)}\n"
        f"Total workouts: {len(workouts_first) + len(workouts_second)}\n"
        f"Weight: {user.get('weight_kg', '?')} kg"
    )


def _exec_suggest_workout(args: dict, user_id: int) -> str:
    conn = _connect()
    user_row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    user = dict(user_row) if user_row else {}

    recent = [dict(r) for r in conn.execute(
        "SELECT type, duration_min, date FROM workouts WHERE user_id=? AND date>=? ORDER BY date DESC LIMIT 5",
        (user_id, (date.today() - timedelta(days=7)).isoformat()),
    ).fetchall()]
    conn.close()

    recent_text = ", ".join(f"{w['type']} {w['duration_min']}min ({w['date']})" for w in recent) or "None this week"
    day = now_local().strftime("%A")

    return (
        f"CONTEXT FOR WORKOUT SUGGESTION:\n"
        f"User: {user.get('name', '?')}, {user.get('age', '?')}y, {user.get('weight_kg', '?')}kg\n"
        f"Goal: {user.get('goal', 'maintain')}\n"
        f"Today: {day}\n"
        f"Recent workouts: {recent_text}\n"
        f"Focus: {args.get('focus', 'any')}"
    )


def _exec_suggest_meal(args: dict, user_id: int) -> str:
    conn = _connect()
    user_row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    user = dict(user_row) if user_row else {}

    today_meals = [dict(r) for r in conn.execute(
        "SELECT total_cal FROM meals WHERE user_id=? AND date=?", (user_id, _today())
    ).fetchall()]
    conn.close()

    eaten_cal = sum(m["total_cal"] for m in today_meals)
    target_cal = {"fat_loss": 1600, "muscle_gain": 2500, "maintain": 2000}.get(user.get("goal", "maintain"), 2000)
    remaining = max(0, target_cal - eaten_cal)

    hour = now_local().hour
    default_meal = "breakfast" if hour < 11 else "lunch" if hour < 15 else "snack" if hour < 18 else "dinner"
    meal_type = args.get("meal_type", default_meal)

    return (
        f"CONTEXT FOR MEAL SUGGESTION:\n"
        f"User: {user.get('name', '?')}, Diet: {user.get('dietary_prefs', 'any')}\n"
        f"Goal: {user.get('goal', 'maintain')}\n"
        f"Eaten today: {eaten_cal:.0f} kcal | Remaining: ~{remaining:.0f} kcal\n"
        f"Meal type: {meal_type}"
    )


def _exec_update_plan(args: dict, user_id: int) -> str:
    field = args.get("field", "")
    value = args.get("value", "")

    if not field or not value:
        return "ERROR: field and value are required"

    # Validate field
    allowed = {"goal", "weight_kg", "dietary_prefs", "wake_time", "sleep_time"}
    if field not in allowed:
        return f"ERROR: can only update {', '.join(allowed)}"

    # Type coerce weight
    if field == "weight_kg":
        try:
            value = float(value)
        except ValueError:
            return "ERROR: weight must be a number"

    conn = _connect()
    conn.execute(f"UPDATE users SET {field} = ?, updated_at = datetime('now') WHERE id = ?", (value, user_id))
    conn.commit()
    conn.close()

    return f"UPDATED: {field} → {value}"


def _exec_save_preference(args: dict, user_id: int) -> str:
    import os
    note = args.get("note", "").strip()
    if not note:
        return "ERROR: empty note"

    summary_path = os.path.join("data", "user_summary.txt")
    os.makedirs("data", exist_ok=True)

    # Read existing, avoid duplicates
    existing = ""
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            existing = f.read()

    if note.lower() in existing.lower():
        return f"ALREADY NOTED: {note}"

    with open(summary_path, "a", encoding="utf-8") as f:
        f.write(f"- {note}\n")

    return f"SAVED PREFERENCE: {note}"


def _exec_delete_entry(args: dict, user_id: int) -> str:
    entry_type = args.get("entry_type", "")
    entry_id = args.get("entry_id", 0)

    if not entry_type or not entry_id:
        return "ERROR: entry_type and entry_id are required"

    table_map = {
        "meal": "meals",
        "exercise": "workouts",
        "habit": "habits",
    }

    table = table_map.get(entry_type)
    if not table:
        return f"ERROR: invalid entry_type '{entry_type}'. Use: meal, exercise, or habit"

    conn = _connect()

    # Verify the entry belongs to this user
    row = conn.execute(f"SELECT id FROM {table} WHERE id=? AND user_id=?", (entry_id, user_id)).fetchone()
    if not row:
        conn.close()
        return f"ERROR: No {entry_type} entry found with id={entry_id} for this user"

    # Delete associated meal_items if it's a meal
    if entry_type == "meal":
        conn.execute("DELETE FROM meal_items WHERE meal_id=?", (entry_id,))

    conn.execute(f"DELETE FROM {table} WHERE id=? AND user_id=?", (entry_id, user_id))
    conn.commit()
    conn.close()

    return f"DELETED: {entry_type} entry id={entry_id} has been removed"


def _exec_generate_dashboard(args: dict, user_id: int) -> str:
    days = args.get("days", 1)
    if days < 1:
        days = 1

    try:
        from telegram_bot.dashboard_image import generate_dashboard_image
        img_path = generate_dashboard_image(user_id, days)
        period = "today" if days == 1 else f"the last {days} days"
        return (
            f"DASHBOARD_IMAGE:{img_path}\n"
            f"Dashboard generated for {period}. "
            f"The image shows calories, protein, exercise, habit score, and trends."
        )
    except Exception as e:
        return f"Error generating dashboard: {str(e)}"
