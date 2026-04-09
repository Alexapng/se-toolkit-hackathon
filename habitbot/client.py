from __future__ import annotations

import argparse
import json
import shlex
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ApiError(RuntimeError):
    pass


class HabitApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_users(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/users")
        return data["users"]

    def create_user(self, name: str) -> dict[str, Any]:
        return self._request("POST", "/users", {"name": name})

    def add_habit(self, user_id: int, name: str) -> dict[str, Any]:
        return self._request("POST", "/habits", {"user_id": user_id, "name": name})

    def list_habits(self, user_id: int) -> list[dict[str, Any]]:
        query = urlencode({"user_id": user_id})
        data = self._request("GET", f"/habits?{query}")
        return data["habits"]

    def check_in(self, habit_id: int, checkin_date: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"habit_id": habit_id}
        if checkin_date:
            payload["date"] = checkin_date
        return self._request("POST", "/checkins", payload)

    def daily_status(self, user_id: int, checkin_date: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"user_id": user_id}
        if checkin_date:
            params["date"] = checkin_date
        query = urlencode(params)
        return self._request("GET", f"/status?{query}")

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        data: bytes | None = None
        headers: dict[str, str] = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = Request(url=url, method=method, data=data, headers=headers)

        try:
            with urlopen(req, timeout=10) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            message = f"HTTP error {exc.code}"
            body = exc.read().decode("utf-8")
            if body:
                try:
                    parsed = json.loads(body)
                    if isinstance(parsed, dict) and "error" in parsed:
                        message = str(parsed["error"])
                except json.JSONDecodeError:
                    pass
            raise ApiError(message) from exc
        except URLError as exc:
            raise ApiError(f"cannot connect to backend: {exc.reason}") from exc


HELP_TEXT = """
Commands:
  help
  users
  create-user <name>
  use-user <user_id>
  add-habit <habit name>
  habits
  check-in <habit_id> [YYYY-MM-DD]
  today [YYYY-MM-DD]
  exit
"""


def run_cli(api: HabitApiClient) -> None:
    active_user_id: int | None = None
    print("Minimal Habit Bot")
    print("Type 'help' for commands.")

    while True:
        raw = input("habit-bot> ").strip()
        if not raw:
            continue

        try:
            parts = shlex.split(raw)
        except ValueError as exc:
            print(f"Invalid command syntax: {exc}")
            continue

        command = parts[0].lower()
        args = parts[1:]

        try:
            if command in {"exit", "quit"}:
                print("Bye.")
                return

            if command == "help":
                print(HELP_TEXT.strip())
                continue

            if command == "users":
                users = api.list_users()
                if not users:
                    print("No users yet. Create one with: create-user <name>")
                    continue
                for user in users:
                    marker = "*" if active_user_id == user["id"] else " "
                    print(f"{marker} {user['id']}: {user['name']}")
                continue

            if command == "create-user":
                if not args:
                    print("Usage: create-user <name>")
                    continue
                user_name = " ".join(args)
                user = api.create_user(user_name)
                active_user_id = int(user["id"])
                print(f"Created user #{user['id']} ({user['name']}). Active user updated.")
                continue

            if command == "use-user":
                if len(args) != 1:
                    print("Usage: use-user <user_id>")
                    continue
                active_user_id = int(args[0])
                print(f"Active user set to #{active_user_id}.")
                continue

            if command == "add-habit":
                if active_user_id is None:
                    print("Set active user first with: create-user <name> or use-user <id>")
                    continue
                if not args:
                    print("Usage: add-habit <habit name>")
                    continue
                habit = api.add_habit(active_user_id, " ".join(args))
                print(f"Added habit #{habit['id']}: {habit['name']}")
                continue

            if command == "habits":
                if active_user_id is None:
                    print("Set active user first with: create-user <name> or use-user <id>")
                    continue
                habits = api.list_habits(active_user_id)
                if not habits:
                    print("No habits yet. Add one with: add-habit <habit name>")
                    continue
                for habit in habits:
                    print(f"{habit['id']}: {habit['name']}")
                continue

            if command == "check-in":
                if len(args) not in {1, 2}:
                    print("Usage: check-in <habit_id> [YYYY-MM-DD]")
                    continue
                habit_id = int(args[0])
                checkin_date = args[1] if len(args) == 2 else None
                checkin = api.check_in(habit_id, checkin_date)
                print(
                    f"Check-in saved for habit #{checkin['habit_id']} "
                    f"on {checkin['checkin_date']}."
                )
                continue

            if command == "today":
                if active_user_id is None:
                    print("Set active user first with: create-user <name> or use-user <id>")
                    continue
                if len(args) > 1:
                    print("Usage: today [YYYY-MM-DD]")
                    continue
                checkin_date = args[0] if args else None
                status = api.daily_status(active_user_id, checkin_date)
                print(f"Daily status for user #{status['user_id']} on {status['date']}:")
                if not status["habits"]:
                    print("No habits to show.")
                    continue
                for item in status["habits"]:
                    marker = "[x]" if item["completed"] else "[ ]"
                    print(f"{marker} {item['habit_id']}: {item['habit_name']}")
                continue

            print("Unknown command. Type 'help' for available commands.")

        except ValueError:
            print("Invalid numeric value in command.")
        except ApiError as exc:
            print(f"API error: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the terminal client for the minimal habit bot.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Backend API base URL (default: http://127.0.0.1:8000).",
    )
    args = parser.parse_args()
    run_cli(HabitApiClient(args.base_url))


if __name__ == "__main__":
    main()

