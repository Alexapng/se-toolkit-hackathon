#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="habitbot"
SERVICE_USER="${USER}"
HOST="0.0.0.0"
PORT="8000"

usage() {
  cat <<'USAGE'
Usage:
  ./deploy/install_systemd.sh [--service-name NAME] [--user USER] [--host HOST] [--port PORT]

Examples:
  ./deploy/install_systemd.sh
  ./deploy/install_systemd.sh --service-name habitbot --user ubuntu --port 8000
USAGE
}

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
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
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

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required. Install it first: sudo apt update && sudo apt install -y python3" >&2
  exit 1
fi

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  echo "User '$SERVICE_USER' does not exist on this VM." >&2
  exit 1
fi

if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
  echo "Port must be a number, got: $PORT" >&2
  exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="$(command -v python3)"
SERVICE_GROUP="$(id -gn "$SERVICE_USER")"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

TMP_UNIT="$(mktemp)"
cat > "$TMP_UNIT" <<EOF
[Unit]
Description=Minimal Habit Bot API
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PYTHON_BIN} -m habitbot.api --host ${HOST} --port ${PORT} --db-path ${PROJECT_DIR}/habitbot.db
Restart=always
RestartSec=3
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
echo "Service installed and running."
echo "Status:"
sudo systemctl --no-pager --full status "$SERVICE_NAME"
echo
echo "Useful commands:"
echo "  sudo systemctl restart ${SERVICE_NAME}"
echo "  sudo systemctl stop ${SERVICE_NAME}"
echo "  sudo systemctl start ${SERVICE_NAME}"
echo "  sudo journalctl -u ${SERVICE_NAME} -f"
echo "  curl http://127.0.0.1:${PORT}/health"

