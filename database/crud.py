"""
CRUD operations for the Healthy Agent database.
Uses synchronous sqlite3.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

import sqlite3

from config import DB_PATH


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def _today() -> str:
    return date.today().isoformat()


# ──────────────────────────────────────────────────────────────────
# USERS
# ──────────────────────────────────────────────────────────────────

def get_user_by_telegram_id(telegram_id: int) -> Optional[dict]:
    with _connect() as db:
        cursor = db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_first_user(onboarded_only: bool = True) -> Optional[dict]:
    """Get the first (or only) onboarded user, prioritizing Telegram users."""
    conn = _connect()
    where = "WHERE onboarding_done = 1" if onboarded_only else ""
    # Order by telegram_id DESC to prioritize real users (ID > 0) over placeholder (ID=0)
    cursor = conn.execute(f"SELECT * FROM users {where} ORDER BY telegram_id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    with _connect() as db:
        cursor = db.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def create_user(telegram_id: int, name: str = "") -> int:
    with _connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO users (telegram_id, name) VALUES (?, ?)",
            (telegram_id, name),
        )
        db.commit()
        # Return the user id
        cursor2 = db.execute(
            "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = cursor2.fetchone()
        return row["id"]


def update_user(telegram_id: int, **fields) -> None:
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [telegram_id]
    with _connect() as db:
        db.execute(
            f"UPDATE users SET {set_clause}, updated_at = datetime('now') WHERE telegram_id = ?",
            values,
        )
        db.commit()


def delete_user(telegram_id: int) -> None:
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return
    uid = user["id"]
    with _connect() as db:
        # Cascade manually
        db.execute("DELETE FROM chat_history WHERE user_id = ?", (uid,))
        db.execute("DELETE FROM daily_scores WHERE user_id = ?", (uid,))
        db.execute("DELETE FROM habits WHERE user_id = ?", (uid,))
        db.execute(
            "DELETE FROM meal_items WHERE meal_id IN (SELECT id FROM meals WHERE user_id = ?)",
            (uid,),
        )
        db.execute("DELETE FROM meals WHERE user_id = ?", (uid,))
        db.execute("DELETE FROM workouts WHERE user_id = ?", (uid,))
        db.execute("DELETE FROM users WHERE id = ?", (uid,))
        db.commit()


# ──────────────────────────────────────────────────────────────────
# WORKOUTS
# ──────────────────────────────────────────────────────────────────

def log_workout(
    user_id: int,
    workout_type: str = "",
    duration_min: int = 0,
    intensity: str = "moderate",
    planned: str = "",
    notes: str = "",
    date_str: str | None = None,
) -> int:
    with _connect() as db:
        cursor = db.execute(
            """INSERT INTO workouts (user_id, date, type, duration_min, intensity, planned, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, date_str or _today(), workout_type, duration_min, intensity, planned, notes),
        )
        db.commit()
        return cursor.lastrowid


def update_workout_completion(workout_id: int, completed: bool) -> None:
    with _connect() as db:
        db.execute(
            "UPDATE workouts SET completed = ? WHERE id = ?",
            (int(completed), workout_id),
        )
        db.commit()


def get_workouts(user_id: int, days: int = 7) -> list[dict]:
    with _connect() as db:
        cursor = db.execute(
            """SELECT * FROM workouts
               WHERE user_id = ? AND date >= date('now', ?)
               ORDER BY date DESC""",
            (user_id, f"-{days} days"),
        )
        return [dict(r) for r in cursor.fetchall()]


def get_today_workouts(user_id: int) -> list[dict]:
    with _connect() as db:
        cursor = db.execute(
            "SELECT * FROM workouts WHERE user_id = ? AND date = ?",
            (user_id, _today()),
        )
        return [dict(r) for r in cursor.fetchall()]


# ──────────────────────────────────────────────────────────────────
# MEALS
# ──────────────────────────────────────────────────────────────────

def log_meal(
    user_id: int,
    meal_type: str,
    raw_text: str,
    total_cal: float = 0,
    protein_g: float = 0,
    carb_g: float = 0,
    fat_g: float = 0,
    date_str: str | None = None,
) -> int:
    with _connect() as db:
        cursor = db.execute(
            """INSERT INTO meals (user_id, date, meal_type, raw_text, total_cal, protein_g, carb_g, fat_g)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, date_str or _today(), meal_type, raw_text, total_cal, protein_g, carb_g, fat_g),
        )
        db.commit()
        return cursor.lastrowid


def add_meal_items(meal_id: int, items: list[dict]) -> None:
    with _connect() as db:
        for item in items:
            db.execute(
                """INSERT INTO meal_items (meal_id, food_name, quantity_g, cal, protein_g, carb_g, fat_g)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    meal_id,
                    item.get("food_name", ""),
                    item.get("quantity_g", 0),
                    item.get("cal", 0),
                    item.get("protein_g", 0),
                    item.get("carb_g", 0),
                    item.get("fat_g", 0),
                ),
            )
        db.commit()


def get_today_meals(user_id: int) -> list[dict]:
    with _connect() as db:
        cursor = db.execute(
            "SELECT * FROM meals WHERE user_id = ? AND date = ? ORDER BY created_at",
            (user_id, _today()),
        )
        return [dict(r) for r in cursor.fetchall()]


def get_meals(user_id: int, days: int = 7) -> list[dict]:
    with _connect() as db:
        cursor = db.execute(
            """SELECT * FROM meals
               WHERE user_id = ? AND date >= date('now', ?)
               ORDER BY date DESC""",
            (user_id, f"-{days} days"),
        )
        return [dict(r) for r in cursor.fetchall()]


def get_meal_items(meal_id: int) -> list[dict]:
    with _connect() as db:
        cursor = db.execute(
            "SELECT * FROM meal_items WHERE meal_id = ?", (meal_id,)
        )
        return [dict(r) for r in cursor.fetchall()]


# ──────────────────────────────────────────────────────────────────
# HABITS
# ──────────────────────────────────────────────────────────────────

def log_habits(
    user_id: int,
    screen_time_min: int = 0,
    junk_desc: str = "",
    junk_cal: float = 0,
    sleep_hours: float = 0,
    water_glasses: int = 0,
    notes: str = "",
    date_str: str | None = None,
) -> int:
    with _connect() as db:
        cursor = db.execute(
            """INSERT INTO habits (user_id, date, screen_time_min, junk_desc, junk_cal, sleep_hours, water_glasses, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, date_str or _today(), screen_time_min, junk_desc, junk_cal, sleep_hours, water_glasses, notes),
        )
        db.commit()
        return cursor.lastrowid


def get_today_habits(user_id: int) -> Optional[dict]:
    with _connect() as db:
        cursor = db.execute(
            "SELECT * FROM habits WHERE user_id = ? AND date = ? ORDER BY created_at DESC LIMIT 1",
            (user_id, _today()),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_habits(user_id: int, days: int = 7) -> list[dict]:
    with _connect() as db:
        cursor = db.execute(
            """SELECT * FROM habits
               WHERE user_id = ? AND date >= date('now', ?)
               ORDER BY date DESC""",
            (user_id, f"-{days} days"),
        )
        return [dict(r) for r in cursor.fetchall()]


def compute_habit_score(habits_data: dict) -> int:
    """Compute a score (0-100) based on daily habit metrics."""
    if not habits_data:
        return 0
    
    score = 50
    sleep = habits_data.get("sleep_hours", 0)
    screen = habits_data.get("screen_time_min", 0)
    water = habits_data.get("water_glasses", 0)
    junk_cal = habits_data.get("junk_cal", 0)

    # Sleep (20 pts)
    if 7 <= sleep <= 9: score += 20
    elif 6 <= sleep < 7: score += 10
    elif sleep < 5: score -= 10

    # Screen Time (15 pts)
    if screen <= 60: score += 15
    elif screen <= 120: score += 5
    elif screen > 240: score -= 10

    # Water (15 pts)
    if water >= 8: score += 15
    elif water >= 5: score += 5
    elif water < 3: score -= 5

    # Junk (10 pts)
    if junk_cal == 0: score += 10
    elif junk_cal > 500: score -= 15

    return max(0, min(100, score))


# ──────────────────────────────────────────────────────────────────
# DAILY SCORES
# ──────────────────────────────────────────────────────────────────

def save_daily_score(
    user_id: int,
    exercise_score: float = 0,
    nutrition_score: float = 0,
    habit_score: float = 0,
    overall_score: float = 0,
    llm_feedback: str = "",
    date_str: str | None = None,
) -> None:
    d = date_str or _today()
    with _connect() as db:
        db.execute(
            """INSERT INTO daily_scores (user_id, date, exercise_score, nutrition_score, habit_score, overall_score, llm_feedback)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(date) DO UPDATE SET
                   exercise_score = excluded.exercise_score,
                   nutrition_score = excluded.nutrition_score,
                   habit_score = excluded.habit_score,
                   overall_score = excluded.overall_score,
                   llm_feedback = excluded.llm_feedback""",
            (user_id, d, exercise_score, nutrition_score, habit_score, overall_score, llm_feedback),
        )
        db.commit()


def get_daily_scores(user_id: int, days: int = 7) -> list[dict]:
    with _connect() as db:
        cursor = db.execute(
            """SELECT * FROM daily_scores
               WHERE user_id = ? AND date >= date('now', ?)
               ORDER BY date DESC""",
            (user_id, f"-{days} days"),
        )
        return [dict(r) for r in cursor.fetchall()]


# ──────────────────────────────────────────────────────────────────
# AGGREGATED STATS (for LLM context)
# ──────────────────────────────────────────────────────────────────

def get_weekly_stats(user_id: int) -> dict[str, Any]:
    """Return a compact stats dict for the last 7 days, used in LLM prompts."""
    meals = get_meals(user_id, days=7)
    workouts = get_workouts(user_id, days=7)
    habits = get_habits(user_id, days=7)
    scores = get_daily_scores(user_id, days=7)

    total_cal = sum(m.get("total_cal", 0) for m in meals)
    total_protein = sum(m.get("protein_g", 0) for m in meals)
    meal_days = len(set(m["date"] for m in meals)) or 1

    workouts_completed = sum(1 for w in workouts if w.get("completed"))

    avg_habit = (
        sum(s.get("habit_score", 0) for s in scores) / len(scores)
        if scores else 0
    )

    return {
        "avg_cal": round(total_cal / meal_days),
        "avg_protein": round(total_protein / meal_days),
        "workouts_completed": workouts_completed,
        "workouts_total": len(workouts),
        "avg_habit_score": round(avg_habit, 1),
        "days_tracked": meal_days,
    }


# ──────────────────────────────────────────────────────────────────
# API USAGE TRACKING
# ──────────────────────────────────────────────────────────────────

def track_api_usage(request_count: int = 1, token_count: int = 0) -> None:
    now = datetime.now()
    d = now.strftime("%Y-%m-%d")
    h = now.hour
    with _connect() as db:
        db.execute(
            """INSERT INTO api_usage (date, hour, request_count, token_count)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(date, hour) DO UPDATE SET
                   request_count = api_usage.request_count + excluded.request_count,
                   token_count = api_usage.token_count + excluded.token_count""",
            (d, h, request_count, token_count),
        )
        db.commit()


def get_daily_api_usage() -> dict[str, int]:
    d = _today()
    with _connect() as db:
        cursor = db.execute(
            "SELECT SUM(request_count) as reqs, SUM(token_count) as toks FROM api_usage WHERE date = ?",
            (d,),
        )
        row = cursor.fetchone()
        return {
            "requests": row["reqs"] or 0,
            "tokens": row["toks"] or 0,
        }


# ──────────────────────────────────────────────────────────────────
# CHAT HISTORY
# ──────────────────────────────────────────────────────────────────

def save_chat_message(user_id: int, role: str, content: str) -> None:
    with _connect() as db:
        db.execute(
            "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )
        db.commit()


def get_chat_history(user_id: int, limit: int = 50) -> list[dict]:
    with _connect() as db:
        cursor = db.execute(
            """SELECT role, content, created_at FROM chat_history
               WHERE user_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit),
        )
        rows = [dict(r) for r in cursor.fetchall()]
        return list(reversed(rows))  # oldest first


def export_all_user_data(user_id: int) -> dict[str, list[dict]]:
    """Export all data for a user as a dict of table_name -> rows."""
    user = get_user_by_id(user_id)
    meals = get_meals(user_id, days=365)
    workouts = get_workouts(user_id, days=365)
    habits = get_habits(user_id, days=365)
    scores = get_daily_scores(user_id, days=365)

    return {
        "user": [user] if user else [],
        "meals": meals,
        "workouts": workouts,
        "habits": habits,
        "daily_scores": scores,
    }
