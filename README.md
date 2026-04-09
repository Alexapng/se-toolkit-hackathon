# Minimal Habit Bot

Track daily completion of small habits with a lightweight backend API, SQLite database, and terminal bot client.

## Product Context

- End user: people who want to build better daily habits.
- Problem: users struggle to stay consistent with small daily actions.
- Solution: a minimal habit bot to check in each selected habit every day.

## Version 1 Scope (Task 3)

- Core feature implemented: daily check-in for selected habits.
- Components:
  - backend API: `habitbot/api.py`
  - database: SQLite (`habitbot.db`)
  - client: terminal bot (`habitbot/client.py`)

## Run Locally

1. Start backend:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; $env:UV_PYTHON_INSTALL_DIR='.uv-python'; uv run --python 3.12 python -m habitbot.api --host 127.0.0.1 --port 8000
```

2. In a second terminal, start client:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; $env:UV_PYTHON_INSTALL_DIR='.uv-python'; uv run --python 3.12 python -m habitbot.client --base-url http://127.0.0.1:8000
```

3. Example commands in client:

```text
create-user Alex
add-habit Drink water
add-habit Read 10 pages
habits
check-in 1
today
```

## Test

```powershell
$env:UV_CACHE_DIR='.uv-cache'; $env:UV_PYTHON_INSTALL_DIR='.uv-python'; uv run --python 3.12 python -m unittest discover -s tests -v
```

