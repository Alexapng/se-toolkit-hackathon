#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="habitbot-telegram"
SERVICE_USER="${USER}"
TIMEZONE="Europe/Moscow"
WEB_APP_URL="${TELEGRAM_WEB_APP_URL:-}"
BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"

usage() {
  cat <<'USAGE'
Usage:
  ./deploy/install_telegram_bot_systemd.sh --token <BOT_TOKEN> --web-app-url <HTTPS_URL> [options]

Options:
  --service-name <name>   Systemd service name (default: habitbot-telegram)
  --user <name>           Linux user to run the bot as (default: current user)
  --timezone <name>       Notification timezone (default: Europe/Moscow)
  --db-path <path>        SQLite database path (default: <project>/habitbot.db)
  --token <token>         Telegram bot token (or TELEGRAM_BOT_TOKEN env var)
  --web-app-url <url>     Public HTTPS URL for Telegram Mini App button
USAGE
}

DB_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --service-name)
      SERVICE_NAME="$2"
      shift 2
      ;;
    --user)
      SERVICE_USER="$2"
      shift 2
      ;;
    --timezone)
      TIMEZONE="$2"
      shift 2
      ;;
    --db-path)
      DB_PATH="$2"
      shift 2
      ;;
    --token)
      BOT_TOKEN="$2"
      shift 2
      ;;
    --web-app-url)
      WEB_APP_URL="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="$(command -v python3)"
SERVICE_GROUP="$(id -gn "$SERVICE_USER")"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
ENV_PATH="/etc/${SERVICE_NAME}.env"

if [[ -z "$DB_PATH" ]]; then
  DB_PATH="${PROJECT_DIR}/habitbot.db"
fi

if [[ -z "$BOT_TOKEN" ]]; then
  echo "Telegram bot token is required." >&2
  exit 1
fi

if [[ -z "$WEB_APP_URL" ]]; then
  echo "Web app URL is required." >&2
  exit 1
fi

if [[ "$WEB_APP_URL" != https://* ]]; then
  echo "Web app URL must be HTTPS for Telegram Mini App." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required. Install it first: sudo apt update && sudo apt install -y python3" >&2
  exit 1
fi

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  echo "User '$SERVICE_USER' does not exist on this VM." >&2
  exit 1
fi

echo "Writing environment file: ${ENV_PATH}"
TMP_ENV="$(mktemp)"
cat > "$TMP_ENV" <<EOF
TELEGRAM_BOT_TOKEN=${BOT_TOKEN}
TELEGRAM_WEB_APP_URL=${WEB_APP_URL}
TELEGRAM_NOTIFY_TIMEZONE=${TIMEZONE}
HABITBOT_DB_PATH=${DB_PATH}
EOF
sudo install -m 0600 "$TMP_ENV" "$ENV_PATH"
rm -f "$TMP_ENV"

TMP_UNIT="$(mktemp)"
cat > "$TMP_UNIT" <<EOF
[Unit]
Description=Habit Bot Telegram Service
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${ENV_PATH}
ExecStart=${PYTHON_BIN} -m habitbot.telegram_bot
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

echo "Installing systemd service: ${SERVICE_NAME}"
sudo install -m 0644 "$TMP_UNIT" "$UNIT_PATH"
rm -f "$TMP_UNIT"

sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo
echo "Telegram bot service installed and running."
echo "Status:"
sudo systemctl --no-pager --full status "$SERVICE_NAME"
echo
echo "Useful commands:"
echo "  sudo systemctl restart ${SERVICE_NAME}"
echo "  sudo systemctl stop ${SERVICE_NAME}"
echo "  sudo systemctl start ${SERVICE_NAME}"
echo "  sudo journalctl -u ${SERVICE_NAME} -f"

