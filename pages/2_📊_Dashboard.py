"""
📊 Dashboard — Visual health stats and trends.
"""

import streamlit as st
import plotly.graph_objects as go
from datetime import date
from database import crud

st.set_page_config(page_title="Dashboard - HealthyBot", page_icon="📊", layout="wide")
st.title("📊 Health Dashboard")

user = crud.get_first_user()

if not user:
    st.warning("Please complete your profile in **⚙️ Settings** first!")
    st.stop()

days = st.selectbox("Time range", [7, 14, 30], index=0, format_func=lambda x: f"Last {x} days")

meals = crud.get_meals(user["id"], days=days)
workouts = crud.get_workouts(user["id"], days=days)
habits = crud.get_habits(user["id"], days=days)

st.markdown("---")

# ── TODAY'S OVERVIEW ──
st.markdown("### 📅 Today")
today_meals = [m for m in meals if m["date"] == date.today().isoformat()]
today_workouts = [w for w in workouts if w["date"] == date.today().isoformat()]

col1, col2, col3, col4 = st.columns(4)

today_cal = sum(m["total_cal"] for m in today_meals)
today_protein = sum(m["protein_g"] for m in today_meals)
today_carb = sum(m["carb_g"] for m in today_meals)
today_fat = sum(m["fat_g"] for m in today_meals)
target_cal = {"fat_loss": 1600, "muscle_gain": 2500, "maintain": 2000}.get(user.get("goal", "maintain"), 2000)

col1.metric("🔥 Calories", f"{today_cal:.0f} / {target_cal}")
col2.metric("💪 Protein", f"{today_protein:.0f}g")
col3.metric("🍚 Carbs", f"{today_carb:.0f}g")
col4.metric("🧈 Fat", f"{today_fat:.0f}g")

if today_cal > 0:
    fig_pie = go.Figure(data=[go.Pie(
        labels=["Protein", "Carbs", "Fat"],
        values=[today_protein * 4, today_carb * 4, today_fat * 9],
        marker_colors=["#FF6B6B", "#4ECDC4", "#FFE66D"],
        hole=0.4,
        textinfo="label+percent",
    )])
    fig_pie.update_layout(title="Today's Macro Split (by calories)", height=300, margin=dict(t=30, b=0, l=0, r=0), showlegend=False)
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

st.markdown(f"### 📈 Calorie Trend (Last {days} days)")

if meals:
    cal_by_date = {}
    for m in meals:
        cal_by_date.setdefault(m["date"], 0)
        cal_by_date[m["date"]] += m["total_cal"]

    dates = sorted(cal_by_date.keys())
    cals = [cal_by_date[d] for d in dates]

    fig_cal = go.Figure()
    fig_cal.add_trace(go.Scatter(x=dates, y=cals, mode="lines+markers", line=dict(color="#FF6B6B", width=3), marker=dict(size=8), name="Calories"))
    fig_cal.add_hline(y=target_cal, line_dash="dash", line_color="gray", annotation_text=f"Target: {target_cal}")
    fig_cal.update_layout(yaxis_title="Calories (kcal)", height=350, margin=dict(t=10, b=30))
    st.plotly_chart(fig_cal, use_container_width=True)
else:
    st.info("No meal data yet. Start logging meals in the **💬 Chat** page!")

if meals:
    st.markdown("### 💪 Protein Trend")
    pro_by_date = {}
    for m in meals:
        pro_by_date.setdefault(m["date"], 0)
        pro_by_date[m["date"]] += m["protein_g"]

    dates = sorted(pro_by_date.keys())
    proteins = [pro_by_date[d] for d in dates]

    fig_pro = go.Figure()
    fig_pro.add_trace(go.Bar(x=dates, y=proteins, marker_color="#4ECDC4", name="Protein (g)"))
    fig_pro.update_layout(yaxis_title="Protein (g)", height=300, margin=dict(t=10, b=30))
    st.plotly_chart(fig_pro, use_container_width=True)

st.markdown("### 🏋️ Workouts")

if workouts:
    w_col1, w_col2, w_col3 = st.columns(3)
    total_min = sum(w["duration_min"] for w in workouts)
    completed = sum(1 for w in workouts if w["completed"])
    w_col1.metric("Total Sessions", len(workouts))
    w_col2.metric("Completed", f"{completed}/{len(workouts)}")
    w_col3.metric("Total Minutes", total_min)

    types = {}
    for w in workouts:
        t = w.get("type", "other")
        types[t] = types.get(t, 0) + 1

    if types:
        fig_wtype = go.Figure(data=[go.Pie(labels=list(types.keys()), values=list(types.values()), marker_colors=["#FF6B6B", "#4ECDC4", "#FFE66D", "#45B7D1", "#96CEB4"], hole=0.3)])
        fig_wtype.update_layout(title="Workout Types", height=250, margin=dict(t=30, b=0))
        st.plotly_chart(fig_wtype, use_container_width=True)
else:
    st.info("No workout data yet. Log exercise in the **💬 Chat** page!")

st.markdown("### 📱 Habits")

if habits:
    h_col1, h_col2, h_col3 = st.columns(3)
    
    # Calculate averages based on non-zero records for each habit
    sleep_records = [h["sleep_hours"] for h in habits if h["sleep_hours"] > 0]
    avg_sleep = sum(sleep_records) / len(sleep_records) if sleep_records else 0
    
    screen_records = [h["screen_time_min"] for h in habits if h["screen_time_min"] > 0]
    avg_screen = sum(screen_records) / len(screen_records) if screen_records else 0
    
    water_records = [h["water_glasses"] for h in habits if h["water_glasses"] > 0]
    avg_water = sum(water_records) / len(water_records) if water_records else 0
    
    h_col1.metric("Avg Sleep", f"{avg_sleep:.1f} hrs")
    h_col2.metric("Avg Screen Time", f"{avg_screen:.0f} min")
    h_col3.metric("Avg Water", f"{avg_water:.0f} glasses")

    sleep_dates = [h["date"] for h in sorted(habits, key=lambda x: x["date"])]
    sleep_vals = [h["sleep_hours"] for h in sorted(habits, key=lambda x: x["date"])]

    fig_sleep = go.Figure()
    fig_sleep.add_trace(go.Scatter(x=sleep_dates, y=sleep_vals, mode="lines+markers", line=dict(color="#9B59B6", width=3), name="Sleep Hours"))
    fig_sleep.add_hline(y=7, line_dash="dash", line_color="green", annotation_text="Ideal: 7+ hrs")
    fig_sleep.update_layout(yaxis_title="Hours", height=250, margin=dict(t=10, b=30))
    st.plotly_chart(fig_sleep, use_container_width=True)
else:
    st.info("No habit data yet. Log habits in the **💬 Chat** page!")
