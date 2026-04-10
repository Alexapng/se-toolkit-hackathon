# Task 5 Slides Draft

Use this as ready content for your 5-slide PDF.

## Slide 1 - Title

- Product title: `Minimal Habit Bot`
- Name: `Alexandra Pokhvalova`
- University email: `a.pokhvalova@innopolis.university`
- Group: `CSE-01`

## Slide 2 - Context

- End user: people who want to build better daily habits.
- Problem: users struggle to stay consistent with small daily actions.
- Product idea (one sentence): a minimal Telegram Mini App + bot that helps users check daily habits and keep streaks.

## Slide 3 - Implementation

- Stack:
  - Backend: Python (`http.server`) + service layer.
  - Database: SQLite.
  - Client: Telegram Mini App web frontend (HTML/CSS/JS).
  - Bot: Telegram bot with reminders.
- Version 1 (Task 3):
  - Daily check-in for selected habits.
  - Add habits and mark completion by date.
- Version 2 (Task 4):
  - Streak counter + motivational message.
  - Habit deletion.
  - Telegram `/start` profile linking with `@username`.
  - Daily reminder commands (`/notify_on`, `/notify_off`).
- TA feedback addressed:
  - Moved from CLI-like flow to web app.
  - Removed shared activity/active users view.
  - Personalized single-user Telegram-based profile flow.

## Slide 4 - Demo (Video up to 2 minutes)

- 0:00 - 0:15: open bot, send `/start`, open Mini App.
- 0:15 - 0:40: show Telegram username auto-linked (no manual username input).
- 0:40 - 1:05: add 1-2 habits.
- 1:05 - 1:25: check in habits for today.
- 1:25 - 1:40: show streak message (`Yay! Great job!...`).
- 1:40 - 1:55: delete a habit and show immediate UI update.
- 1:55 - 2:00: show reminder commands in bot (`/notify_on`, `/streak`).

## Slide 5 - Links

- GitHub repo:
  - `https://github.com/Alexapng/se-toolkit-hackathon`
- Deployed product:
  - `<YOUR_DEPLOYED_HTTPS_URL>`
- QR codes:
  - GitHub QR: `<ATTACH_GITHUB_QR_IMAGE>`
  - Deployed app QR: `<ATTACH_DEPLOYED_APP_QR_IMAGE>`

If `qrencode` is installed:

```bash
qrencode -o github-qr.png "https://github.com/Alexapng/se-toolkit-hackathon"
qrencode -o app-qr.png "https://<YOUR_DEPLOYED_HTTPS_URL>"
```
