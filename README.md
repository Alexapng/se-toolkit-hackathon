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

## Run Locally

1. Start backend + web app server:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; $env:UV_PYTHON_INSTALL_DIR='.uv-python'; uv run --python 3.12 python -m habitbot.api --host 127.0.0.1 --port 8000
```

2. Open the web app in browser:

`http://127.0.0.1:8000/`

3. In the web app:

- Enter your name and click `Use` (this creates your account if needed).
- Add habits and check in for today.

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
