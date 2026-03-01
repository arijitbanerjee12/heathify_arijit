"""
Streamlit entry point.
Run with: python -m streamlit run run_streamlit.py
"""

import streamlit as st

# Must be the first Streamlit call
st.set_page_config(
    page_title="HealthyBot 🏋️",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database on startup
from database.models import init_db

@st.cache_resource
def _init():
    init_db()

_init()


# ──────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────
st.sidebar.title("💪 HealthyBot")
st.sidebar.markdown("Your AI Health Coach")
st.sidebar.markdown("---")

# ──────────────────────────────────────────────────────────────────
# Main page — Quick Overview
# ──────────────────────────────────────────────────────────────────
st.title("💪 HealthyBot Dashboard")
st.markdown("### Your AI-Powered Health Coach")
st.markdown("---")

from database import crud

user = crud.get_first_user()

if not user:
    st.warning("👋 Welcome! Please complete your profile in the **⚙️ Settings** page first.")
    st.markdown(
        """
        ### Getting Started:
        1. Go to **⚙️ Settings** in the sidebar
        2. Fill in your profile information
        3. Come back here to see your dashboard!

        Or use the **💬 Chat** page to talk to your AI coach directly.
        """
    )
else:
    st.success(f"Welcome back, **{user.get('name', 'there')}**! 👋")

    user_id = user["id"]
    stats = crud.get_weekly_stats(user_id)
    today_meals = crud.get_today_meals(user_id)
    today_workouts = crud.get_today_workouts(user_id)
    today_habits = crud.get_today_habits(user_id)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        today_cal = sum(m["total_cal"] for m in today_meals)
        target_cal = {"fat_loss": 1600, "muscle_gain": 2500, "maintain": 2000}.get(user.get("goal", "maintain"), 2000)
        st.metric("🔥 Calories Today", f"{today_cal:.0f}", f"Target: {target_cal}")

    with col2:
        today_protein = sum(m["protein_g"] for m in today_meals)
        st.metric("💪 Protein Today", f"{today_protein:.0f}g")

    with col3:
        workout_min = sum(w["duration_min"] for w in today_workouts)
        st.metric("🏋️ Exercise", f"{workout_min} min", f"{len(today_workouts)} sessions")

    with col4:
        habit_score = crud.compute_habit_score(today_habits) if today_habits else 0
        st.metric("📊 Habit Score", f"{habit_score:.0f}/100")

    st.markdown("---")

    st.markdown("### 📈 This Week")
    wcol1, wcol2, wcol3 = st.columns(3)

    with wcol1:
        st.metric("Avg Calories/Day", f"{stats['avg_cal']}")
    with wcol2:
        st.metric("Workouts Done", f"{stats['workouts_completed']}/{stats['workouts_total']}")
    with wcol3:
        st.metric("Avg Habit Score", f"{stats['avg_habit_score']}")

    st.markdown("---")
    st.info("💡 Use the **💬 Chat** page to log meals, exercise, and habits — just talk naturally!")
