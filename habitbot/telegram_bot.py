from __future__ import annotations

import argparse
import json
import os
import threading
import time
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .service import HabitService


class TelegramBot:
    def __init__(
        self,
        token: str,
        service: HabitService,
        web_app_url: str | None,
        timezone_name: str,
        poll_timeout: int = 25,
    ) -> None:
        self._token = token
        self._service = service
        self._web_app_url = (web_app_url or "").strip() or None
        self._timezone = ZoneInfo(timezone_name)
        self._poll_timeout = poll_timeout
        self._stop_event = threading.Event()
        self._offset = 0
        self._api_base = f"https://api.telegram.org/bot{token}"

    def run(self) -> None:
        self._set_bot_commands()
        notify_thread = threading.Thread(target=self._notifications_loop, daemon=True)
        notify_thread.start()

        print("Telegram bot started. Press Ctrl+C to stop.")
        while not self._stop_event.is_set():
            try:
                updates = self._api_request(
                    "getUpdates",
                    {
                        "offset": self._offset,
                        "timeout": self._poll_timeout,
                        "allowed_updates": ["message"],
                    },
                )
            except Exception as exc:  # noqa: BLE001
                print(f"[telegram] getUpdates failed: {exc}")
                self._stop_event.wait(3)
                continue

            for update in updates:
                self._offset = max(self._offset, int(update["update_id"]) + 1)
                self._handle_update(update)

    def stop(self) -> None:
        self._stop_event.set()

    def _set_bot_commands(self) -> None:
        commands = [
            {"command": "start", "description": "Link your profile and open mini app"},
            {"command": "streak", "description": "Show your current streak"},
            {"command": "notify_on", "description": "Enable daily reminders (/notify_on 20)"},
            {"command": "notify_off", "description": "Disable daily reminders"},
            {"command": "open", "description": "Send mini app button again"},
            {"command": "help", "description": "Show commands"},
        ]
        try:
            self._api_request("setMyCommands", {"commands": commands})
        except Exception as exc:  # noqa: BLE001
            print(f"[telegram] setMyCommands failed: {exc}")

    def _api_request(self, method: str, payload: dict[str, Any] | None = None) -> Any:
        url = f"{self._api_base}/{method}"
        body = json.dumps(payload or {}).encode("utf-8")
        request = Request(
            url=url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=35) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"telegram API error {exc.code}: {details}") from exc
        except URLError as exc:
            raise RuntimeError(f"telegram API network error: {exc.reason}") from exc

        parsed = json.loads(raw)
        if not parsed.get("ok"):
            raise RuntimeError(f"telegram API method {method} failed: {parsed}")
        return parsed.get("result")

    def _send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        self._api_request("sendMessage", payload)

    def _open_app_markup(self) -> dict[str, Any] | None:
        if not self._web_app_url:
            return None
        return {
            "inline_keyboard": [
                [
                    {
                        "text": "Open Habit Mini App",
                        "web_app": {"url": self._web_app_url},
                    }
                ]
            ]
        }

    def _handle_update(self, update: dict[str, Any]) -> None:
        message = update.get("message")
        if not isinstance(message, dict):
            return

        text = str(message.get("text") or "").strip()
        if not text:
            return

        chat = message.get("chat") or {}
        user = message.get("from") or {}
        chat_id = int(chat.get("id"))

        command = text.split(maxsplit=1)[0].split("@")[0].lower()
        argument = text.split(maxsplit=1)[1].strip() if " " in text else ""

        try:
            if command == "/start":
                self._handle_start(chat_id=chat_id, telegram_user=user)
            elif command == "/help":
                self._handle_help(chat_id)
            elif command == "/open":
                self._handle_open(chat_id)
            elif command == "/streak":
                self._handle_streak(chat_id=chat_id, telegram_user_id=int(user.get("id")))
            elif command == "/notify_on":
                self._handle_notify_on(
                    chat_id=chat_id,
                    telegram_user_id=int(user.get("id")),
                    argument=argument,
                )
            elif command == "/notify_off":
                self._handle_notify_off(chat_id=chat_id, telegram_user_id=int(user.get("id")))
            else:
                self._handle_help(chat_id)
        except Exception as exc:  # noqa: BLE001
            print(f"[telegram] command failed: {exc}")
            self._send_message(chat_id, f"Error: {exc}")

    def _handle_start(self, chat_id: int, telegram_user: dict[str, Any]) -> None:
        telegram_user_id = int(telegram_user.get("id"))
        username = (telegram_user.get("username") or "").strip() or None
        if username is None:
            self._send_message(
                chat_id,
                "Your Telegram account has no @username yet. "
                "Set it in Telegram settings and send /start again.",
            )
            return

        linked = self._service.register_telegram_profile(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            profile_name=username,
            username=username,
        )

        welcome_lines = [
            f"Hi, @{username}!",
            f"Your profile is linked as: {linked['user_name']}",
            "Use /streak to check progress and /notify_on or /notify_off for reminders.",
        ]
        if self._web_app_url:
            welcome_lines.append("Tap the button below to open your Habit Mini App.")
        else:
            welcome_lines.append("Set TELEGRAM_WEB_APP_URL to enable the Mini App button.")

        self._send_message(
            chat_id=chat_id,
            text="\n".join(welcome_lines),
            reply_markup=self._open_app_markup(),
        )

    def _handle_help(self, chat_id: int) -> None:
        text = "\n".join(
            [
                "Commands:",
                "/start - link Telegram to your habit profile",
                "/open - open Mini App button",
                "/streak - show current streak",
                "/notify_on [hour] - enable daily reminders (0..23, default 20)",
                "/notify_off - disable daily reminders",
            ]
        )
        self._send_message(chat_id, text, reply_markup=self._open_app_markup())

    def _handle_open(self, chat_id: int) -> None:
        if not self._web_app_url:
            self._send_message(chat_id, "Mini App URL is not configured yet.")
            return
        self._send_message(chat_id, "Open your Habit Mini App:", reply_markup=self._open_app_markup())

    def _handle_streak(self, chat_id: int, telegram_user_id: int) -> None:
        profile = self._service.get_telegram_profile(telegram_user_id)
        status = self._service.daily_status(profile["user_id"], None)
        streak_days = int(status["streak"]["current_streak_days"])
        completed = int(status["summary"]["completed_habits"])
        total = int(status["summary"]["total_habits"])

        lines = [
            f"Current streak: {streak_days} day{'s' if streak_days != 1 else ''}",
            f"Today's progress: {completed}/{total}",
            str(status["message"]),
        ]
        self._send_message(chat_id, "\n".join(lines), reply_markup=self._open_app_markup())

    def _handle_notify_on(self, chat_id: int, telegram_user_id: int, argument: str) -> None:
        hour = 20
        if argument:
            try:
                hour = int(argument)
            except ValueError as exc:
                raise ValueError("Usage: /notify_on [hour], where hour is 0..23") from exc

        profile = self._service.set_telegram_notifications(
            telegram_user_id=telegram_user_id,
            enabled=True,
            notification_hour=hour,
        )
        self._send_message(
            chat_id,
            (
                f"Daily reminders enabled at {profile['notification_hour']:02d}:00 "
                f"({self._timezone}). I'll remind you to check pending habits."
            ),
            reply_markup=self._open_app_markup(),
        )

    def _handle_notify_off(self, chat_id: int, telegram_user_id: int) -> None:
        self._service.set_telegram_notifications(
            telegram_user_id=telegram_user_id,
            enabled=False,
            notification_hour=None,
        )
        self._send_message(chat_id, "Daily reminders disabled.")

    def _notifications_loop(self) -> None:
        while not self._stop_event.is_set():
            now = datetime.now(self._timezone)
            today = now.date().isoformat()
            hour = now.hour

            try:
                targets = self._service.list_telegram_notification_targets(current_date=today, hour=hour)
                for target in targets:
                    status = self._service.daily_status(int(target["user_id"]), today)
                    text = self._build_reminder_text(
                        user_name=str(target["user_name"]),
                        status=status,
                    )
                    self._send_message(
                        int(target["chat_id"]),
                        text,
                        reply_markup=self._open_app_markup(),
                    )
                    self._service.mark_telegram_notification_sent(
                        telegram_user_id=int(target["telegram_user_id"]),
                        current_date=today,
                    )
            except Exception as exc:  # noqa: BLE001
                print(f"[telegram] notifications loop error: {exc}")

            self._stop_event.wait(60)

    @staticmethod
    def _build_reminder_text(user_name: str, status: dict[str, Any]) -> str:
        summary = status.get("summary") or {}
        streak = status.get("streak") or {}
        completed = int(summary.get("completed_habits") or 0)
        total = int(summary.get("total_habits") or 0)
        streak_days = int(streak.get("current_streak_days") or 0)

        pending_habits: list[str] = []
        for item in status.get("habits") or []:
            if bool(item.get("completed")):
                continue
            name = str(item.get("habit_name") or "").strip()
            if name:
                pending_habits.append(name)

        lines: list[str]
        if total == 0:
            lines = [
                f"Hi, {user_name}!",
                "You do not have habits yet.",
                "Open the Mini App and add your first habit today.",
            ]
        elif completed >= total:
            lines = [
                f"Great job, {user_name}!",
                f"All habits are done today: {completed}/{total}.",
                f"Current streak: {streak_days} day{'s' if streak_days != 1 else ''}.",
                "Come back tomorrow to keep your streak alive.",
            ]
        else:
            pending = ", ".join(pending_habits) if pending_habits else "some habits"
            lines = [
                f"Habit check-in reminder for {user_name}:",
                f"Today's progress: {completed}/{total}.",
                f"Still pending: {pending}.",
                f"Current streak: {streak_days} day{'s' if streak_days != 1 else ''}.",
                "Open the Mini App and finish today's check-ins.",
            ]

        status_message = str(status.get("message") or "").strip()
        if status_message:
            lines.append(status_message)
        return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Telegram bot for the Habit Mini App.")
    parser.add_argument(
        "--token",
        default=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        help="Telegram bot token. Can also be set via TELEGRAM_BOT_TOKEN.",
    )
    parser.add_argument(
        "--db-path",
        default=os.getenv("HABITBOT_DB_PATH", "habitbot.db"),
        help="Path to SQLite database.",
    )
    parser.add_argument(
        "--web-app-url",
        default=os.getenv("TELEGRAM_WEB_APP_URL", "").strip(),
        help="Public HTTPS URL of the web app for Telegram Mini App button.",
    )
    parser.add_argument(
        "--timezone",
        default=os.getenv("TELEGRAM_NOTIFY_TIMEZONE", "Europe/Moscow"),
        help="Timezone used for daily reminders (default: Europe/Moscow).",
    )
    args = parser.parse_args()

    if not args.token:
        raise SystemExit("Missing Telegram bot token. Set TELEGRAM_BOT_TOKEN or pass --token.")

    service = HabitService(db_path=args.db_path)
    bot = TelegramBot(
        token=args.token,
        service=service,
        web_app_url=args.web_app_url,
        timezone_name=args.timezone,
    )

    try:
        bot.run()
    except KeyboardInterrupt:
        print("\nStopping Telegram bot.")
        bot.stop()


if __name__ == "__main__":
    main()
