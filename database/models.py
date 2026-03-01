"""
SQLite database schema — creates all tables on startup.
"""

import sqlite3
from config import DB_PATH


SQL_CREATE_TABLES = """
-- User profile
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id     INTEGER UNIQUE,
    name            TEXT NOT NULL DEFAULT '',
    age             INTEGER,
    gender          TEXT,
    height_cm       REAL,
    weight_kg       REAL,
    goal            TEXT DEFAULT 'maintain',
    wake_time       TEXT DEFAULT '07:00',
    sleep_time      TEXT DEFAULT '23:00',
    dietary_prefs   TEXT DEFAULT '',
    timezone        TEXT DEFAULT 'Asia/Kolkata',
    onboarding_done INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- Workout logs
CREATE TABLE IF NOT EXISTS workouts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    date            TEXT NOT NULL,
    type            TEXT DEFAULT '',
    duration_min    INTEGER DEFAULT 0,
    intensity       TEXT DEFAULT 'moderate',
    planned         TEXT DEFAULT '',
    completed       INTEGER DEFAULT 0,
    notes           TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Meal logs (one row per meal occasion)
CREATE TABLE IF NOT EXISTS meals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    date            TEXT NOT NULL,
    meal_type       TEXT DEFAULT 'other',
    raw_text        TEXT DEFAULT '',
    total_cal       REAL DEFAULT 0,
    protein_g       REAL DEFAULT 0,
    carb_g          REAL DEFAULT 0,
    fat_g           REAL DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Individual food items within a meal
CREATE TABLE IF NOT EXISTS meal_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    meal_id         INTEGER NOT NULL REFERENCES meals(id),
    food_name       TEXT NOT NULL,
    quantity_g      REAL DEFAULT 0,
    cal             REAL DEFAULT 0,
    protein_g       REAL DEFAULT 0,
    carb_g          REAL DEFAULT 0,
    fat_g           REAL DEFAULT 0
);

-- Daily habit check-ins
CREATE TABLE IF NOT EXISTS habits (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    date            TEXT NOT NULL,
    screen_time_min INTEGER DEFAULT 0,
    junk_desc       TEXT DEFAULT '',
    junk_cal        REAL DEFAULT 0,
    sleep_hours     REAL DEFAULT 0,
    water_glasses   INTEGER DEFAULT 0,
    notes           TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Daily computed scores
CREATE TABLE IF NOT EXISTS daily_scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    date            TEXT NOT NULL UNIQUE,
    exercise_score  REAL DEFAULT 0,
    nutrition_score REAL DEFAULT 0,
    habit_score     REAL DEFAULT 0,
    overall_score   REAL DEFAULT 0,
    llm_feedback    TEXT DEFAULT ''
);

-- API usage tracking (for rate limiting)
CREATE TABLE IF NOT EXISTS api_usage (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,
    hour            INTEGER NOT NULL,
    request_count   INTEGER DEFAULT 0,
    token_count     INTEGER DEFAULT 0,
    UNIQUE(date, hour)
);

-- Chat history (for Streamlit cross-session persistence)
CREATE TABLE IF NOT EXISTS chat_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now'))
);
"""


def init_db() -> None:
    """Create all tables if they don't exist (sync)."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SQL_CREATE_TABLES)
    conn.commit()
    conn.close()
