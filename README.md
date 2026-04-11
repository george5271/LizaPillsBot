# LizaPillsBot 💊

A personal Telegram bot that reminds Liza to take her pill and go to sleep on time.
Built with [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) and APScheduler.

---

## Features

- **Pill reminders** — scheduled messages at configurable times
- **Persistent nudges** — keeps reminding on a set interval until the pill is marked
- **Sleep reminders** — bedtime countdown with image messages
- **Streak tracking** — celebrates consecutive days taken
- **Monthly calendar** — visual emoji grid of the whole month
- **Admin panel** — full control via Telegram commands (schedule, interval, manual messages)
- **Weekly stats** — automatic Sunday recap

---

## Project Structure

```
LizaPillsBot/
├── bot.py          # Entry point: handlers, reminders, scheduler, main()
├── config.py       # Loads .env secrets + defines all constants
├── content.py      # All text pools and image URLs
├── storage.py      # DataStorage class — JSON persistence with atomic writes
├── .env            # ⚠️ Secrets (NOT in git)
├── .env.example    # Template for .env
├── .gitignore
├── requirements.txt
└── liza_data.json  # Created automatically on first run (NOT in git)
```

---

## Setup

### 1. Clone the repo

```bash
git clone <repo_url>
cd LizaPillsBot
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure `.env`

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | How to get it |
|---|---|
| `BOT_TOKEN` | Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` or `/token` |
| `ADMIN_CHAT_ID` | Message [@userinfobot](https://t.me/userinfobot) — it replies with your numeric Telegram ID |

> ⚠️ **If you previously had the token hard-coded in source, regenerate it via BotFather before running.**

### 5. Run

```bash
python bot.py
```

Liza sends `/start` to register. You (the admin) send `/start` from a separate account that matches `ADMIN_CHAT_ID`.

---

## Admin Commands

| Command | Description |
|---|---|
| `/status` | Show current pill status, streak, and schedules |
| `/set_pill_schedule 13:00 13:10 13:20` | Set pill reminder times |
| `/set_pill_interval 10` | Set persistent reminder interval (minutes) |
| `/set_sleep_schedule 22:00 23:00 00:00` | Set sleep reminder times (first = question, rest = reminders) |
| `/reset_pill` | Reset pill settings to defaults |
| `/reset_sleep` | Reset sleep settings to defaults |
| `/send_motivation Hello!` | Send a custom motivation message with a random image |
| `/send_text Hello!` | Send a plain text message to Liza |

---

## Running as a Background Service (optional)

To keep the bot alive after closing your terminal, use `screen`, `tmux`, or a `systemd` service:

```bash
# Quick option with screen
screen -S lizabot
python bot.py
# Detach: Ctrl+A, D
```
