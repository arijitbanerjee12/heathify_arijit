"""
Dashboard Image Generator — creates a visual health dashboard as a PNG.
Uses matplotlib to generate an infographic from database data.
"""

import io
import os
import sqlite3
from datetime import date, timedelta

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

from config import DB_PATH
from utils.helpers import now_local


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def generate_dashboard_image(user_id: int, days: int = 1) -> str:
    """
    Generate a dashboard infographic for the given user and time period.
    
    Args:
        user_id: Database user ID
        days: Number of days to show (1 = today, 7 = week, etc.)
    
    Returns:
        Absolute file path to the generated PNG image.
    """
    conn = _connect()

    # ── Fetch user profile ──
    user_row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    user = dict(user_row) if user_row else {"name": "User", "goal": "maintain"}

    today = date.today()
    start_date = (today - timedelta(days=max(0, days - 1))).isoformat()
    end_date = today.isoformat()

    # ── Fetch data ──
    meals = [dict(r) for r in conn.execute(
        "SELECT date, total_cal, protein_g, carb_g, fat_g FROM meals WHERE user_id=? AND date>=? AND date<=? ORDER BY date",
        (user_id, start_date, end_date),
    ).fetchall()]

    workouts = [dict(r) for r in conn.execute(
        "SELECT date, type, duration_min, intensity FROM workouts WHERE user_id=? AND date>=? AND date<=?",
        (user_id, start_date, end_date),
    ).fetchall()]

    habits = [dict(r) for r in conn.execute(
        "SELECT date, sleep_hours, screen_time_min, water_glasses, junk_cal FROM habits WHERE user_id=? AND date>=? AND date<=?",
        (user_id, start_date, end_date),
    ).fetchall()]

    conn.close()

    # ── Compute aggregates ──
    total_cal = sum(m["total_cal"] for m in meals)
    total_protein = sum(m["protein_g"] for m in meals)
    total_carb = sum(m.get("carb_g", 0) for m in meals)
    total_fat = sum(m.get("fat_g", 0) for m in meals)
    num_meals = len(meals)

    total_exercise_min = sum(w["duration_min"] for w in workouts)
    num_workouts = len(workouts)

    avg_sleep = sum(h["sleep_hours"] for h in habits) / len(habits) if habits else 0
    total_water = sum(h["water_glasses"] for h in habits)
    avg_screen = sum(h["screen_time_min"] for h in habits) / len(habits) if habits else 0

    target_cal_per_day = {"fat_loss": 1600, "muscle_gain": 2500, "maintain": 2000}.get(user.get("goal", "maintain"), 2000)
    target_cal = target_cal_per_day * days

    # ── Habit score ──
    habit_score = 50
    if habits:
        if 7 <= avg_sleep <= 9: habit_score += 20
        elif 6 <= avg_sleep < 7: habit_score += 10
        elif avg_sleep < 5: habit_score -= 10
        if avg_screen <= 60: habit_score += 15
        elif avg_screen <= 120: habit_score += 5
        elif avg_screen > 240: habit_score -= 10
        avg_water = total_water / len(habits)
        if avg_water >= 8: habit_score += 15
        elif avg_water >= 5: habit_score += 5
        elif avg_water < 3: habit_score -= 5
        total_junk = sum(h.get("junk_cal", 0) for h in habits)
        if total_junk == 0: habit_score += 10
        elif total_junk > 500 * days: habit_score -= 15
        habit_score = max(0, min(100, habit_score))

    # ── Color palette ──
    BG_COLOR = "#1a1a2e"
    CARD_COLOR = "#16213e"
    ACCENT = "#0f3460"
    TEXT_COLOR = "#e0e0e0"
    HIGHLIGHT = "#e94560"
    GREEN = "#00d2d3"
    GOLD = "#feca57"
    PURPLE = "#a29bfe"
    ORANGE = "#fd9644"

    # ── Build the figure ──
    fig = plt.figure(figsize=(10, 7), facecolor=BG_COLOR)

    if days == 1:
        title = f"Dashboard -- {today.strftime('%B %d, %Y')}"
    else:
        title = f"Dashboard -- Last {days} Days"

    fig.suptitle(title, fontsize=18, fontweight="bold", color=TEXT_COLOR, y=0.97)
    fig.text(0.5, 0.93, f"{user.get('name', 'User')} • Goal: {user.get('goal', 'maintain').replace('_', ' ').title()}",
             fontsize=11, color="#888", ha="center")

    gs = GridSpec(2, 4, figure=fig, hspace=0.4, wspace=0.35,
                  top=0.88, bottom=0.08, left=0.06, right=0.94)

    def _card_ax(gs_pos):
        ax = fig.add_subplot(gs_pos)
        ax.set_facecolor(CARD_COLOR)
        for spine in ax.spines.values():
            spine.set_color(ACCENT)
            spine.set_linewidth(1.5)
        ax.tick_params(colors=TEXT_COLOR, labelsize=8)
        return ax

    # ── Card 1: Calories ──
    ax1 = _card_ax(gs[0, 0])
    cal_pct = min(total_cal / target_cal, 1.0) if target_cal > 0 else 0
    color = GREEN if 0.8 <= cal_pct <= 1.1 else GOLD if cal_pct < 0.8 else HIGHLIGHT
    ax1.barh([0], [cal_pct], height=0.5, color=color, alpha=0.85, zorder=2)
    ax1.barh([0], [1.0], height=0.5, color=ACCENT, alpha=0.4, zorder=1)
    ax1.set_xlim(0, 1.2)
    ax1.set_yticks([])
    ax1.set_xticks([])
    ax1.text(0.5, 0.85, "CALORIES", transform=ax1.transAxes, fontsize=12,
             fontweight="bold", color=TEXT_COLOR, ha="center", va="top")
    ax1.text(0.5, -0.25, f"{total_cal:.0f} / {target_cal:.0f} kcal",
             transform=ax1.transAxes, fontsize=10, color=color, ha="center")

    # ── Card 2: Protein ──
    ax2 = _card_ax(gs[0, 1])
    ax2.set_xticks([])
    ax2.set_yticks([])
    ax2.text(0.5, 0.7, "P", transform=ax2.transAxes, fontsize=32, ha="center", va="center",
             fontweight="bold", color=GREEN, alpha=0.3)
    ax2.text(0.5, 0.35, f"{total_protein:.0f}g", transform=ax2.transAxes,
             fontsize=22, fontweight="bold", color=GREEN, ha="center", va="center")
    ax2.text(0.5, 0.05, "Protein", transform=ax2.transAxes, fontsize=10, color="#888", ha="center")

    # ── Card 3: Exercise ──
    ax3 = _card_ax(gs[0, 2])
    ax3.set_xticks([])
    ax3.set_yticks([])
    ax3.text(0.5, 0.7, "E", transform=ax3.transAxes, fontsize=32, ha="center", va="center",
             fontweight="bold", color=PURPLE, alpha=0.3)
    ax3.text(0.5, 0.35, f"{total_exercise_min} min", transform=ax3.transAxes,
             fontsize=20, fontweight="bold", color=PURPLE, ha="center", va="center")
    ax3.text(0.5, 0.05, f"{num_workouts} session{'s' if num_workouts != 1 else ''}",
             transform=ax3.transAxes, fontsize=10, color="#888", ha="center")

    # ── Card 4: Habit Score ──
    ax4 = _card_ax(gs[0, 3])
    ax4.set_xticks([])
    ax4.set_yticks([])
    score_color = GREEN if habit_score >= 70 else GOLD if habit_score >= 50 else HIGHLIGHT
    ax4.text(0.5, 0.7, "H", transform=ax4.transAxes, fontsize=32, ha="center", va="center",
             fontweight="bold", color=score_color, alpha=0.3)
    ax4.text(0.5, 0.35, f"{habit_score}/100", transform=ax4.transAxes,
             fontsize=22, fontweight="bold", color=score_color, ha="center", va="center")
    ax4.text(0.5, 0.05, "Habit Score", transform=ax4.transAxes, fontsize=10, color="#888", ha="center")

    # ── Row 2: Daily calorie trend (bar chart) ──
    ax5 = _card_ax(gs[1, :3])

    # Group calories by date
    cal_by_date = {}
    for d_offset in range(days):
        d = (today - timedelta(days=days - 1 - d_offset)).isoformat()
        cal_by_date[d] = 0
    for m in meals:
        cal_by_date[m["date"]] = cal_by_date.get(m["date"], 0) + m["total_cal"]

    dates = list(cal_by_date.keys())
    cals = list(cal_by_date.values())
    bar_colors = [GREEN if 0.8 * target_cal_per_day <= c <= 1.1 * target_cal_per_day
                  else GOLD if c < 0.8 * target_cal_per_day
                  else HIGHLIGHT for c in cals]

    if days == 1:
        # For single day, show macro breakdown instead
        macros = [total_protein, total_carb, total_fat]
        macro_labels = ["Protein", "Carbs", "Fat"]
        macro_colors = [GREEN, GOLD, ORANGE]
        bars = ax5.bar(macro_labels, macros, color=macro_colors, alpha=0.85, width=0.5)
        for bar, val in zip(bars, macros):
            ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                     f"{val:.0f}g", ha="center", fontsize=10, color=TEXT_COLOR, fontweight="bold")
        ax5.set_title("Macro Breakdown", fontsize=12, fontweight="bold", color=TEXT_COLOR, pad=10)
        ax5.set_ylabel("grams", fontsize=9, color="#888")
    else:
        x_labels = [d[-5:] for d in dates]  # MM-DD
        bars = ax5.bar(x_labels, cals, color=bar_colors, alpha=0.85, width=0.6)
        ax5.axhline(y=target_cal_per_day, color=HIGHLIGHT, linestyle="--", alpha=0.6, linewidth=1)
        ax5.text(len(dates) - 0.5, target_cal_per_day + 30, f"Target: {target_cal_per_day}",
                 fontsize=8, color=HIGHLIGHT, ha="right")
        for bar, val in zip(bars, cals):
            if val > 0:
                ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20,
                         f"{val:.0f}", ha="center", fontsize=8, color=TEXT_COLOR)
        ax5.set_title("Daily Calories", fontsize=12, fontweight="bold", color=TEXT_COLOR, pad=10)
        ax5.set_ylabel("kcal", fontsize=9, color="#888")

    ax5.tick_params(axis="x", rotation=45 if days > 3 else 0)

    # ── Card 6: Habits summary ──
    ax6 = _card_ax(gs[1, 3])
    ax6.set_xticks([])
    ax6.set_yticks([])
    habit_lines = [
        (f"Sleep: {avg_sleep:.1f}h", GREEN if avg_sleep >= 7 else GOLD),
        (f"Water: {total_water} gl", GREEN if total_water >= 8 * days else GOLD),
        (f"Screen: {avg_screen:.0f} min", GREEN if avg_screen <= 120 else HIGHLIGHT),
        (f"Meals: {num_meals}", TEXT_COLOR),
    ]
    for i, (txt, col) in enumerate(habit_lines):
        ax6.text(0.5, 0.85 - i * 0.22, txt, transform=ax6.transAxes,
                 fontsize=11, color=col, ha="center", va="center", fontweight="bold")
    ax6.text(0.5, -0.05, "Habits", transform=ax6.transAxes, fontsize=10, color="#888", ha="center")

    # ── Save to file ──
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"dashboard_{user_id}.png")

    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close(fig)

    return out_path
