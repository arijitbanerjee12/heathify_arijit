# 💪 HealthyBot — Your AI-Powered Health Coach

An intelligent, conversational health assistant built with **Groq LLM** and delivered through **Telegram + Streamlit**. Just talk naturally — HealthyBot understands what you ate, how you exercised, and how your habits are going, then gives you personalized coaching and visual dashboards.

> **No commands. No forms. Just chat like you're texting a friend who happens to be a nutritionist.**

---

## ✨ Key Features

### 🗣️ Natural Language Everything
Talk in plain English (or Hinglish). The LLM understands context, estimates nutrition for Indian foods, and takes action automatically.

| You say | Bot does |
|---|---|
| "Had 2 rotis, dal and paneer for lunch" | Logs meal with full macro breakdown (cal/protein/carbs/fat) |
| "Did 30 min running and pushups" | Logs exercise with intensity tracking |
| "Slept 5 hours, drank 4 glasses water" | Logs habits, computes health score |
| "What did I eat yesterday?" | Fetches day summary with entry IDs |
| "Show me my dashboard" | Generates and sends a visual infographic |
| "Last 7 days dashboard" | Weekly trend chart with daily calorie bars |
| "Delete that duplicate entry" | Finds and removes incorrect logs |
| "Suggest a workout" | AI-generated plan based on your history |

### 📊 Visual Dashboard (Telegram + Streamlit)
- **Telegram**: Request a dashboard image anytime via natural language — get a dark-themed infographic with calories, protein, exercise, habit score, macro breakdown, and trends.
- **Streamlit**: Full interactive web dashboard with Plotly charts, weekly stats, and profile management.

### ⏰ Automated Daily Messages (Telegram)
| Time | Message |
|---|---|
| 7:00 AM | AI-generated morning motivation + health tip |
| 12:30 PM | Lunch logging reminder |
| 7:30 PM | Dinner logging reminder |
| 10:00 PM | End-of-day summary + dashboard image |
| Sunday 9 PM | Weekly progress review |

### 🧠 Learns & Adapts
- Remembers your dietary preferences, injuries, and routines
- Suggestions evolve as more data accumulates
- Personalized calorie targets based on your goal (fat loss / muscle gain / maintain)

---

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────────────┐     ┌─────────────┐
│  Telegram    │────▶│   Core Agent Engine   │────▶│  Groq API   │
│  (pyTelegramBotAPI) │   (Sync, Tool-based) │     │ GPT-OSS-120B│
└──────────────┘     └──────────┬───────────┘     └─────────────┘
                                │
┌──────────────┐     ┌──────────▼───────────┐
│  Streamlit   │────▶│   SQLite Database    │
│  Dashboard   │     │   (Shared, Local)    │
└──────────────┘     └──────────────────────┘
```

**Fully Synchronous** — no async/await anywhere. Thread-safe for Streamlit + Telegram running simultaneously.

---

## 📁 Project Structure

```
healthy_agent/
├── run_telegram.py              # Telegram bot entry point
├── run_streamlit.py             # Streamlit dashboard entry point
├── config.py                    # Configuration, secrets, LLM presets
├── requirements.txt             # Python dependencies
│
├── core/                        # Shared brain (used by both frontends)
│   ├── agent.py                 # LLM agent with tool calling
│   ├── tools.py                 # 12 tools: log_meal, suggest_workout, generate_dashboard, etc.
│   ├── llm_client.py            # Groq wrapper + rate limiter
│   └── nutrition/               # Food database + calorie calculator
│
├── database/                    # Data layer
│   ├── models.py                # Schema: users, meals, workouts, habits, chat_history
│   └── crud.py                  # All DB operations (synchronous sqlite3)
│
├── telegram_bot/                # Telegram-specific
│   ├── handlers/
│   │   ├── message_handler.py   # Routes messages + sends dashboard images
│   │   └── onboarding.py        # New user profile setup
│   ├── scheduler.py             # Daily automated messages (schedule lib)
│   ├── dashboard_image.py       # Matplotlib infographic generator
│   └── keyboards.py             # Inline keyboard layouts
│
├── pages/                       # Streamlit pages
│   ├── 1_💬_Chat.py             # Chat interface
│   ├── 2_📊_Dashboard.py        # Visual analytics
│   └── 5_⚙️_Settings.py        # Profile management
│
└── utils/                       # Helpers & formatters
```

---

## 🚀 Quick Start

### 1. Install

```bash
cd healthy_agent
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:
```
GROQ_API_KEY=your_key_here          # https://console.groq.com
TELEGRAM_BOT_TOKEN=your_token_here  # @BotFather on Telegram
```

### 3. Run

```bash
# Telegram Bot
python run_telegram.py

# Streamlit Dashboard (separate terminal)
streamlit run run_streamlit.py
```

Both share the same SQLite database — data logged on Telegram appears on Streamlit instantly.

---

## 🔧 Tech Stack

| Component | Technology |
|---|---|
| **LLM** | Groq API — `openai/gpt-oss-120b` (free tier) |
| **Telegram** | pyTelegramBotAPI (synchronous) |
| **Dashboard** | Streamlit + Plotly |
| **Charts** | Matplotlib (for Telegram infographics) |
| **Database** | SQLite (local, zero config) |
| **Scheduler** | `schedule` library + background thread |
| **Language** | Python 3.13 |

---

## 🤝 LLM Tool Calling

HealthyBot uses **Groq's native function calling** with 12 registered tools:

`log_meal` · `log_exercise` · `log_habits` · `get_day_summary` · `get_date_range_data` · `evaluate_progress` · `suggest_workout` · `suggest_meal` · `update_plan` · `save_user_preference` · `delete_entry` · `generate_dashboard`

The LLM decides which tool to call based on the user's natural language — no regex, no intent classification.

---

## 📊 Rate Limits (Free Tier)

| Limit | Value | Typical Daily Usage |
|---|---|---|
| Requests/day | 1,000 | ~26 (2.6%) |
| Tokens/day | 200,000 | ~12K (6%) |

Built-in rate limiter handles throttling automatically.

---

## 🔒 Privacy

All data stays on your machine — SQLite database, no cloud sync, no telemetry.

---

## 📄 License

Personal use. Built with ❤️ and Groq.
