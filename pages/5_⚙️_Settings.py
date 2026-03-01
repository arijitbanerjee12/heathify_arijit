"""
⚙️ Settings — Profile management, data export, onboarding.
"""

import csv
import io
import streamlit as st
from database import crud

st.set_page_config(page_title="Settings - HealthyBot", page_icon="⚙️", layout="wide")
st.title("⚙️ Settings")


user = crud.get_first_user(onboarded_only=False)

# ── ONBOARDING / PROFILE FORM ──
st.markdown("### 👤 Profile")

if user and user.get("onboarding_done"):
    st.success(f"Profile active: **{user.get('name', '')}**")
    editing = st.toggle("Edit profile", value=False)
else:
    st.info("Welcome! Fill in your profile to get started.")
    editing = True
    if not user:
        crud.create_user(telegram_id=0, name="")
        user = crud.get_first_user(onboarded_only=False)

if editing and user:
    with st.form("profile_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Name", value=user.get("name", ""))
            age = st.number_input("Age", min_value=10, max_value=120, value=user.get("age") or 25)
            gender_options = ["male", "female", "other"]
            gender_val = user.get("gender", "male") or "male"
            gender_idx = gender_options.index(gender_val) if gender_val in gender_options else 0
            gender = st.selectbox("Gender", gender_options, index=gender_idx)
            height = st.number_input("Height (cm)", min_value=100.0, max_value=250.0,
                                     value=float(user.get("height_cm") or 170))

        with col2:
            weight = st.number_input("Weight (kg)", min_value=20.0, max_value=250.0,
                                     value=float(user.get("weight_kg") or 70))
            goal_options = ["fat_loss", "muscle_gain", "maintain"]
            goal_labels = {"fat_loss": "🔥 Lose Fat", "muscle_gain": "💪 Gain Muscle", "maintain": "⚖️ Maintain"}
            goal_val = user.get("goal", "maintain") or "maintain"
            goal_idx = goal_options.index(goal_val) if goal_val in goal_options else 2
            goal = st.selectbox("Goal", goal_options, index=goal_idx, format_func=lambda x: goal_labels[x])

            diet_options = ["veg", "egg", "nonveg", "vegan"]
            diet_labels = {"veg": "🥬 Vegetarian", "egg": "🥚 Eggetarian", "nonveg": "🍗 Non-Veg", "vegan": "🌱 Vegan"}
            diet_val = user.get("dietary_prefs", "nonveg") or "nonveg"
            diet_idx = diet_options.index(diet_val) if diet_val in diet_options else 2
            diet = st.selectbox("Dietary Preference", diet_options, index=diet_idx, format_func=lambda x: diet_labels[x])

            wake = st.text_input("Wake time (HH:MM)", value=user.get("wake_time", "07:00") or "07:00")
            sleep_time = st.text_input("Sleep time (HH:MM)", value=user.get("sleep_time", "23:00") or "23:00")

        submitted = st.form_submit_button("💾 Save Profile", use_container_width=True)

        if submitted:
            crud.update_user(
                user["telegram_id"],
                name=name,
                age=age,
                gender=gender,
                height_cm=height,
                weight_kg=weight,
                goal=goal,
                dietary_prefs=diet,
                wake_time=wake,
                sleep_time=sleep_time,
                onboarding_done=1,
            )
            st.success("✅ Profile saved!")
            st.rerun()

st.markdown("---")

# ── DATA EXPORT ──
st.markdown("### 📤 Export Data")

if st.button("📥 Download All Data as CSV"):
    if user:
        data = crud.export_all_user_data(user["id"])

        output = io.StringIO()
        for table_name, rows in data.items():
            if rows:
                output.write(f"\n=== {table_name.upper()} ===\n")
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

        st.download_button(
            label="💾 Download CSV",
            data=output.getvalue(),
            file_name="healthybot_data.csv",
            mime="text/csv",
        )

st.markdown("---")

# ── DANGER ZONE ──
st.markdown("### ⚠️ Danger Zone")

with st.expander("Delete Account", expanded=False):
    st.warning("This will permanently delete ALL your data. This cannot be undone.")
    confirm = st.text_input("Type 'DELETE' to confirm")
    if st.button("🗑️ Delete My Account", type="secondary"):
        if confirm == "DELETE" and user:
            crud.delete_user(user["telegram_id"])
            st.success("Account deleted. Refresh the page.")
            for key in list(st.session_state.keys()):
                del st.session_state[key]
        else:
            st.error("Please type 'DELETE' to confirm.")
