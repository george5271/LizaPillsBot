# LizaPillsBot 💊

A beautifully personalized Telegram bot that reminds Liza to take her pill and go to sleep on time.
Built with [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) and APScheduler.

---

## 🌟 Features

- **Pill reminders** — Scheduled messages with randomized cute texts and 'day' images.
- **Persistent nudges** — Keeps reminding on a set interval until the pill is marked as taken.
- **Sleep routine** — Bedtime countdown with lovely sleep-themed messages and images.
- **Streak tracking** — Celebrates consecutive days taken.
- **Monthly calendar** — Visual emoji grid of the whole month.
- **Admin panel** — Full control via Telegram, including mirroring of all automated messages to the admin.
- **Conversational messaging** — Admin can instantly route custom texts, photos, and captions to Liza via the bot interface.

---

## 📁 Project Structure

```
LizaPillsBot/
├── bot.py          # Core orchestrator: handlers, scheduled jobs, telegram polling
├── config.py       # Configuration layer: Environment variables, timezone, default schedules
├── content.py      # Assets: Massive pools of randomized Russian texts and Yandex image URLs
├── storage.py      # Persistence: Atomic JSON saving and stats calculation
├── .env            # ⚠️ Secrets (Tokens and Chat IDs — Not in Git)
├── .gitignore      # Ignores sensitive keys and local database files
├── requirements.txt# Dependencies
└── liza_data.json  # Runtime database created automatically (Not in Git)
```

---

## 🛠️ Setup & Run

### 1. Requirements

Ensure you are using Python 3 and a virtual environment.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration (`.env`)

You must create a `.env` file in the root directory. This keeps your secure tokens out of version control.

```env
BOT_TOKEN=7XXXXXXXXXXXXXXXXXXXXXXXXXXX
ADMIN_CHAT_ID=111111111  # Your numeric Telegram ID
LIZA_CHAT_ID=222222222   # Liza's numeric Telegram ID
```

*(Note: You can get your numeric Telegram ID by messaging [@userinfobot](https://t.me/userinfobot))*

### 3. Run

```bash
python3 bot.py
```

The console will boot up the APScheduler and output the current schedule and connection status.

---

## 👑 Admin Commands

The bot uses strict access control. Only the account matching `ADMIN_CHAT_ID` can trigger these commands.

| Command | Description |
|---|---|
| `/start` | Setup text showing available commands. |
| `/status` | Shows current pill status for the day, active streak, and the cron schedule. |
| `/calendar` | Prints the same monthly calendar & statistics view that Liza sees. |
| `/send_text` | Initiates a conversational flow. The bot will wait for you to send an image/text, and seamlessly route it to Liza. |
| `/send_message_image [текст]` | Instantly wraps your text with a random image from the `day` pool and sends it to Liza. |

**Monitoring:** Because of the `send_both()` core function, any automated message triggered by the system (pill reminders, sleep reminders, etc.) is immediately forwarded to the Admin with a `📨 [Лизе]` tag.

---

## 🎨 Modifying Content
All user-facing language and images are fiercely separated from the logic. If you want to change what the bot says, simply edit `content.py`.
- `TEXTS`: Contains arrays of phrases for reminders, motivation, and sleep. The bot picks one at random globally.
- `IMAGES`: Contains direct Yandex Disk image URLs securely split into `day` and `sleep` categories.
