from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .service import HabitService


def _build_handler(service: HabitService) -> type[BaseHTTPRequestHandler]:
    web_root = Path(__file__).resolve().parent / "web"

    class HabitApiHandler(BaseHTTPRequestHandler):
        _service = service
        server_version = "HabitBot/0.1"

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)

            try:
                if parsed.path in {"/", "/index.html"}:
                    self._send_static_file(web_root / "index.html", "text/html; charset=utf-8")
                elif parsed.path == "/styles.css":
                    self._send_static_file(web_root / "styles.css", "text/css; charset=utf-8")
                elif parsed.path == "/app.js":
                    self._send_static_file(
                        web_root / "app.js",
                        "application/javascript; charset=utf-8",
                    )
                elif parsed.path == "/health":
                    self._send_json(HTTPStatus.OK, {"status": "ok"})
                elif parsed.path == "/users/lookup":
                    name = self._required_str_param(query, "name")
                    user = self._service.get_user_by_name(name)
                    self._send_json(HTTPStatus.OK, user)
                elif parsed.path == "/users":
                    users = self._service.list_users()
                    self._send_json(HTTPStatus.OK, {"users": users})
                elif parsed.path == "/habits":
                    user_id = self._required_int_param(query, "user_id")
                    habits = self._service.list_habits(user_id)
                    self._send_json(HTTPStatus.OK, {"habits": habits})
                elif parsed.path == "/status":
                    user_id = self._required_int_param(query, "user_id")
                    checkin_date = self._optional_str_param(query, "date")
                    status = self._service.daily_status(user_id, checkin_date)
                    self._send_json(HTTPStatus.OK, status)
                else:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "route not found"})
            except Exception as exc:  # noqa: BLE001
                self._handle_exception(exc)

        def do_POST(self) -> None:  # noqa: N802
            try:
                payload = self._read_json_body()

                if self.path == "/users":
                    name = self._required_str_field(payload, "name")
                    user = self._service.create_user(name)
                    self._send_json(HTTPStatus.CREATED, user)
                elif self.path == "/habits":
                    user_id = self._required_int_field(payload, "user_id")
                    habit_name = self._required_str_field(payload, "name")
                    habit = self._service.add_habit(user_id, habit_name)
                    self._send_json(HTTPStatus.CREATED, habit)
                elif self.path == "/checkins":
                    habit_id = self._required_int_field(payload, "habit_id")
                    checkin_date = self._optional_str_field(payload, "date")
                    checkin = self._service.check_in(habit_id, checkin_date)
                    self._send_json(HTTPStatus.CREATED, checkin)
                else:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "route not found"})
            except Exception as exc:  # noqa: BLE001
                self._handle_exception(exc)

        def do_DELETE(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)

            try:
                if parsed.path == "/habits":
                    user_id = self._required_int_param(query, "user_id")
                    habit_id = self._required_int_param(query, "habit_id")
                    self._service.delete_habit(user_id=user_id, habit_id=habit_id)
                    self._send_json(HTTPStatus.OK, {"status": "deleted"})
                else:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "route not found"})
            except Exception as exc:  # noqa: BLE001
                self._handle_exception(exc)

        def _handle_exception(self, exc: Exception) -> None:
            if isinstance(exc, KeyError):
                field_name = str(exc).strip("'")
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": f"missing required field: {field_name}"},
                )
                return

            if isinstance(exc, ValueError):
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            if isinstance(exc, LookupError):
                self._send_json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
                return

            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal server error"})

        def _send_static_file(self, file_path: Path, content_type: str) -> None:
            if not file_path.exists() or not file_path.is_file():
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "static file not found"})
                return

            body = file_path.read_bytes()
            self.send_response(HTTPStatus.OK.value)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json_body(self) -> dict[str, object]:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                return {}

            raw = self.rfile.read(content_length).decode("utf-8")
            if not raw:
                return {}
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("request body must be valid JSON") from exc
            if not isinstance(data, dict):
                raise ValueError("request body must be a JSON object")
            return data

        def _send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status.value)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        @staticmethod
        def _required_int_field(payload: dict[str, object], field: str) -> int:
            if field not in payload:
                raise KeyError(field)
            try:
                return int(payload[field])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"field '{field}' must be an integer") from exc

        @staticmethod
        def _required_str_field(payload: dict[str, object], field: str) -> str:
            if field not in payload:
                raise KeyError(field)
            value = payload[field]
            if not isinstance(value, str):
                raise ValueError(f"field '{field}' must be a string")
            return value

        @staticmethod
        def _optional_str_field(payload: dict[str, object], field: str) -> str | None:
            value = payload.get(field)
            if value is None:
                return None
            if not isinstance(value, str):
                raise ValueError(f"field '{field}' must be a string")
            return value

        @staticmethod
        def _required_int_param(query: dict[str, list[str]], key: str) -> int:
            values = query.get(key)
            if not values:
                raise ValueError(f"missing query parameter: {key}")
            try:
                return int(values[0])
            except ValueError as exc:
                raise ValueError(f"query parameter '{key}' must be an integer") from exc

        @staticmethod
        def _required_str_param(query: dict[str, list[str]], key: str) -> str:
            values = query.get(key)
            if not values:
                raise ValueError(f"missing query parameter: {key}")
            value = values[0].strip()
            if not value:
                raise ValueError(f"query parameter '{key}' cannot be empty")
            return value

        @staticmethod
        def _optional_str_param(query: dict[str, list[str]], key: str) -> str | None:
            values = query.get(key)
            if not values:
                return None
            return values[0]

    return HabitApiHandler


def run_server(host: str, port: int, db_path: str) -> None:
    service = HabitService(db_path=db_path)
    handler_cls = _build_handler(service)

    with ThreadingHTTPServer((host, port), handler_cls) as server:
        print(f"Habit web app + API is running at http://{host}:{port} (db: {db_path})")
        print("Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the minimal habit bot web app + backend API server.")
    parser.add_argument("--host", default="127.0.0.1", help="Host for API server (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000, help="Port for API server (default: 8000).")
    parser.add_argument(
        "--db-path",
        default="habitbot.db",
        help="Path to SQLite DB file (default: habitbot.db).",
    )
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, db_path=args.db_path)


if __name__ == "__main__":
    main()
