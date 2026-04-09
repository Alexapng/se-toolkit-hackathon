from __future__ import annotations

from datetime import date, datetime, timedelta
import sqlite3
from typing import Any

from .database import get_connection, init_db

Record = dict[str, Any]


def _normalize_date(value: str | None) -> str:
    if value is None:
        return date.today().isoformat()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError("date must be in YYYY-MM-DD format") from exc


class HabitService:
    def __init__(self, db_path: str = "habitbot.db") -> None:
        self.db_path = db_path
        init_db(self.db_path)

    def create_user(self, name: str) -> Record:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("name cannot be empty")

        try:
            with get_connection(self.db_path) as conn:
                cursor = conn.execute("INSERT INTO users(name) VALUES (?)", (clean_name,))
                conn.commit()
                return {"id": cursor.lastrowid, "name": clean_name}
        except sqlite3.IntegrityError as exc:
            raise ValueError("user with this name already exists") from exc

    def list_users(self) -> list[Record]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT id, name FROM users ORDER BY id").fetchall()
            return [dict(row) for row in rows]

    def get_user_by_name(self, name: str) -> Record:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("name cannot be empty")

        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, name FROM users WHERE name = ?",
                (clean_name,),
            ).fetchone()
            if row is None:
                raise LookupError("user not found")
            return dict(row)

    def add_habit(self, user_id: int, name: str) -> Record:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("habit name cannot be empty")

        try:
            with get_connection(self.db_path) as conn:
                self._ensure_user_exists(conn, user_id)
                cursor = conn.execute(
                    "INSERT INTO habits(user_id, name) VALUES (?, ?)",
                    (user_id, clean_name),
                )
                conn.commit()
                return {"id": cursor.lastrowid, "user_id": user_id, "name": clean_name}
        except sqlite3.IntegrityError as exc:
            raise ValueError("habit already exists for this user") from exc

    def list_habits(self, user_id: int) -> list[Record]:
        with get_connection(self.db_path) as conn:
            self._ensure_user_exists(conn, user_id)
            rows = conn.execute(
                "SELECT id, user_id, name, created_at FROM habits WHERE user_id = ? ORDER BY id",
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def check_in(self, habit_id: int, checkin_date: str | None = None) -> Record:
        normalized_date = _normalize_date(checkin_date)
        with get_connection(self.db_path) as conn:
            habit = conn.execute(
                "SELECT id, user_id, name FROM habits WHERE id = ?",
                (habit_id,),
            ).fetchone()
            if habit is None:
                raise LookupError("habit not found")

            conn.execute(
                "INSERT OR IGNORE INTO checkins(habit_id, checkin_date) VALUES (?, ?)",
                (habit_id, normalized_date),
            )
            row = conn.execute(
                """
                SELECT c.id AS checkin_id, h.id AS habit_id, h.name AS habit_name, c.checkin_date
                FROM checkins c
                JOIN habits h ON h.id = c.habit_id
                WHERE c.habit_id = ? AND c.checkin_date = ?
                """,
                (habit_id, normalized_date),
            ).fetchone()
            conn.commit()
            return dict(row)

    def daily_status(self, user_id: int, checkin_date: str | None = None) -> Record:
        normalized_date = _normalize_date(checkin_date)
        target_date = datetime.strptime(normalized_date, "%Y-%m-%d").date()
        with get_connection(self.db_path) as conn:
            self._ensure_user_exists(conn, user_id)
            rows = conn.execute(
                """
                SELECT
                    h.id AS habit_id,
                    h.name AS habit_name,
                    CASE WHEN c.id IS NULL THEN 0 ELSE 1 END AS completed
                FROM habits h
                LEFT JOIN checkins c
                    ON c.habit_id = h.id
                   AND c.checkin_date = ?
                WHERE h.user_id = ?
                ORDER BY h.id
                """,
                (normalized_date, user_id),
            ).fetchall()

            habits = [
                {
                    "habit_id": row["habit_id"],
                    "habit_name": row["habit_name"],
                    "completed": bool(row["completed"]),
                }
                for row in rows
            ]

            total_habits = len(habits)
            completed_habits = sum(1 for item in habits if item["completed"])
            all_done_today = total_habits > 0 and completed_habits == total_habits
            current_streak_days = self._current_streak_days(
                conn=conn,
                user_id=user_id,
                target_date=target_date,
                total_habits=total_habits,
            )
            streak_message = self._streak_message(
                total_habits=total_habits,
                completed_habits=completed_habits,
                current_streak_days=current_streak_days,
            )

            return {
                "user_id": user_id,
                "date": normalized_date,
                "habits": habits,
                "summary": {
                    "completed_habits": completed_habits,
                    "total_habits": total_habits,
                    "all_done_today": all_done_today,
                },
                "streak": {
                    "current_streak_days": current_streak_days,
                    "as_of_date": normalized_date,
                },
                "message": streak_message,
            }

    @staticmethod
    def _current_streak_days(
        conn: sqlite3.Connection,
        user_id: int,
        target_date: date,
        total_habits: int,
    ) -> int:
        if total_habits == 0:
            return 0

        rows = conn.execute(
            """
            SELECT
                c.checkin_date AS checkin_date,
                COUNT(DISTINCT c.habit_id) AS completed_count
            FROM checkins c
            JOIN habits h ON h.id = c.habit_id
            WHERE h.user_id = ?
              AND c.checkin_date <= ?
            GROUP BY c.checkin_date
            ORDER BY c.checkin_date DESC
            """,
            (user_id, target_date.isoformat()),
        ).fetchall()

        completed_by_date = {
            datetime.strptime(row["checkin_date"], "%Y-%m-%d").date(): int(row["completed_count"])
            for row in rows
        }

        streak = 0
        current_date = target_date
        while completed_by_date.get(current_date) == total_habits:
            streak += 1
            current_date -= timedelta(days=1)

        return streak

    @staticmethod
    def _streak_message(total_habits: int, completed_habits: int, current_streak_days: int) -> str:
        if total_habits == 0:
            return "Add your first habit to start a streak."

        if completed_habits == total_habits:
            if current_streak_days == 1:
                return "Yay! Great job! You started your streak today."
            return f"Yay! Great job! You're on a {current_streak_days}-day streak."

        return "Keep going. Complete all habits today to build your streak."

    @staticmethod
    def _ensure_user_exists(conn: sqlite3.Connection, user_id: int) -> None:
        row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise LookupError("user not found")
