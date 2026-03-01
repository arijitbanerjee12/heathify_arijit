"""
Utility helpers — timezone, formatting, etc.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import USER_TIMEZONE


def now_local() -> datetime:
    """Get current datetime in user's timezone."""
    return datetime.now(ZoneInfo(USER_TIMEZONE))


def today_str() -> str:
    """Today's date as ISO string in user's timezone."""
    return now_local().date().isoformat()


def format_macros(cal: float, protein: float, carb: float, fat: float) -> str:
    """Human-readable macro summary."""
    return (
        f"🔥 {cal:.0f} kcal  |  "
        f"💪 {protein:.0f}g protein  |  "
        f"🍚 {carb:.0f}g carbs  |  "
        f"🧈 {fat:.0f}g fat"
    )


def format_habit_score(score: float) -> str:
    """Format habit score with emoji."""
    if score >= 80:
        emoji = "🟢"
    elif score >= 60:
        emoji = "🟡"
    elif score >= 40:
        emoji = "🟠"
    else:
        emoji = "🔴"
    return f"{emoji} Habit Score: {score:.0f}/100"


def format_time(time_str: str) -> str:
    """Format HH:MM string to 12-hour format."""
    try:
        t = datetime.strptime(time_str, "%H:%M")
        return t.strftime("%I:%M %p")
    except ValueError:
        return time_str


def time_until(target_time_str: str) -> timedelta:
    """Calculate timedelta until a target HH:MM time today (or tomorrow if passed)."""
    now = now_local()
    h, m = map(int, target_time_str.split(":"))
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target - now


def truncate(text: str, max_len: int = 200) -> str:
    """Truncate text with ellipsis."""
    return text[:max_len] + "…" if len(text) > max_len else text
