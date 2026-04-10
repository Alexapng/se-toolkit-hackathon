# Minimal Habit Bot

Track daily completion of small habits with a lightweight backend API, SQLite database, and personal web app client.

## Product Context

- End user: people who want to build better daily habits.
- Problem: users struggle to stay consistent with small daily actions.
- Solution: a minimal habit bot to check in each selected habit every day.

## Version 1 Scope (Task 3)

- Core feature implemented: daily check-in for selected habits.
- Components:
  - backend API: `habitbot/api.py`
  - database: SQLite (`habitbot.db`)
  - client: web app (`habitbot/web/index.html`, `habitbot/web/app.js`, `habitbot/web/styles.css`)

## Version 2 Scope (Task 4)

- Added streak counter for consecutive days where all habits are completed.
- Added motivational message in the UI, including:
  - `Yay! Great job! You started your streak today.`
  - `Yay! Great job! You're on a N-day streak.`
- Added habit deletion from the web app.
- Added Telegram bot integration:
  - `/start` links Telegram `@username` to the habit profile name;
  - bot sends Mini App button to open the web app in Telegram;
  - daily Telegram reminders include pending habits and streak info (`/notify_on`, `/notify_off`).

## Run Locally

1. Start backend + web app server:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; $env:UV_PYTHON_INSTALL_DIR='.uv-python'; uv run --python 3.12 python -m habitbot.api --host 127.0.0.1 --port 8000
```

2. Check server health:

`http://127.0.0.1:8000/health`

3. Use it from Telegram Mini App:

- Send `/start` to your bot in Telegram.
- Tap `Open Habit Mini App`.
- The app automatically uses your Telegram `@username`.
- Add habits, delete habits, and check in for today.

## Test

```powershell
$env:UV_CACHE_DIR='.uv-cache'; $env:UV_PYTHON_INSTALL_DIR='.uv-python'; uv run --python 3.12 python -m unittest discover -s tests -v
```

## Run On Ubuntu VM (Auto-Start, No SSH Session Needed)

This setup runs the backend as a `systemd` service, so it keeps working after you log out and after VM reboot.

1. Install dependencies:

```bash
sudo apt update
sudo apt install -y git python3
```

2. Clone repo and switch to your task branch:

```bash
git clone https://github.com/Alexapng/se-toolkit-hackathon.git
cd se-toolkit-hackathon
git checkout feature/task3-habit-bot-v1
```

3. Install and start the service:

```bash
chmod +x deploy/install_systemd.sh
./deploy/install_systemd.sh --service-name habitbot --user "$USER" --host 0.0.0.0 --port 8000
```

4. Verify service health:

```bash
curl http://127.0.0.1:8000/health
sudo systemctl status habitbot
```

5. Allow external access:

```bash
sudo ufw allow 8000/tcp
```

6. Open the web app from your laptop:

`http://<YOUR_VM_PUBLIC_IP>:8000/`

Useful service commands:

```bash
sudo systemctl restart habitbot
sudo systemctl stop habitbot
sudo systemctl start habitbot
sudo journalctl -u habitbot -f
```

## Telegram Mini App Setup

Requirements:

- Telegram bot token from `@BotFather`.
- Public HTTPS URL for your web app (for example `https://your-domain.com`).
- In `@BotFather`, set Mini App URL to the same HTTPS URL.

Run Telegram bot service on VM:

```bash
cd ~/se-toolkit-hackathon
git fetch origin
git checkout feature/task3-habit-bot-v1
git pull
chmod +x deploy/install_telegram_bot_systemd.sh
./deploy/install_telegram_bot_systemd.sh --token "<BOT_TOKEN>" --web-app-url "https://<YOUR_PUBLIC_HTTPS_URL>"
```

Check bot service:

```bash
sudo systemctl status habitbot-telegram
sudo journalctl -u habitbot-telegram -f
```

Mini App cache behavior:

- Frontend assets (`app.js`, `styles.css`) are automatically versioned by the backend.
- After deploying frontend changes, restart `habitbot` and reopen the Mini App in Telegram.
- You do not need to manually add `?v=...` to `TELEGRAM_WEB_APP_URL`.

Supported Telegram commands:

- `/start` - link Telegram account and open Mini App button
- `/open` - send Mini App button again
- `/streak` - current streak summary
- `/notify_on [hour]` - enable daily reminders (hour 0..23, default `20`)
- `/notify_off` - disable daily reminders
