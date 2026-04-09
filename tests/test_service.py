from __future__ import annotations

import os
import unittest
import uuid

from habitbot.service import HabitService


class HabitServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db_path = f"tests/test_{uuid.uuid4().hex}.db"
        self.service = HabitService(self.db_path)

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_create_user_and_add_habit(self) -> None:
        user = self.service.create_user("Alex")
        habit = self.service.add_habit(user["id"], "Drink water")
        habits = self.service.list_habits(user["id"])

        self.assertEqual(habit["name"], "Drink water")
        self.assertEqual(len(habits), 1)
        self.assertEqual(habits[0]["id"], habit["id"])

    def test_get_user_by_name(self) -> None:
        created = self.service.create_user("Alex")
        found = self.service.get_user_by_name("Alex")
        self.assertEqual(found["id"], created["id"])
        self.assertEqual(found["name"], "Alex")

        with self.assertRaises(LookupError):
            self.service.get_user_by_name("Unknown")

    def test_check_in_marks_habit_completed_for_date(self) -> None:
        user = self.service.create_user("Alex")
        habit = self.service.add_habit(user["id"], "Walk 10 minutes")

        self.service.check_in(habit["id"], "2026-04-09")
        status = self.service.daily_status(user["id"], "2026-04-09")

        self.assertEqual(len(status["habits"]), 1)
        self.assertTrue(status["habits"][0]["completed"])
        self.assertEqual(status["summary"]["completed_habits"], 1)
        self.assertEqual(status["summary"]["total_habits"], 1)
        self.assertEqual(status["streak"]["current_streak_days"], 1)
        self.assertIn("Yay! Great job!", status["message"])

    def test_duplicate_check_in_same_day_is_idempotent(self) -> None:
        user = self.service.create_user("Alex")
        habit = self.service.add_habit(user["id"], "Read 10 pages")

        first = self.service.check_in(habit["id"], "2026-04-09")
        second = self.service.check_in(habit["id"], "2026-04-09")

        self.assertEqual(first["checkin_id"], second["checkin_id"])

    def test_invalid_or_missing_entities_raise_clear_errors(self) -> None:
        with self.assertRaises(LookupError):
            self.service.list_habits(999)

        with self.assertRaises(LookupError):
            self.service.check_in(999)

        with self.assertRaises(ValueError):
            self.service.daily_status(999, "09-04-2026")

    def test_streak_requires_all_habits_for_consecutive_days(self) -> None:
        user = self.service.create_user("Alex")
        habit1 = self.service.add_habit(user["id"], "Drink water")
        habit2 = self.service.add_habit(user["id"], "Read 10 pages")

        self.service.check_in(habit1["id"], "2026-04-09")
        self.service.check_in(habit2["id"], "2026-04-09")
        self.service.check_in(habit1["id"], "2026-04-10")
        self.service.check_in(habit2["id"], "2026-04-10")

        status = self.service.daily_status(user["id"], "2026-04-10")
        self.assertEqual(status["streak"]["current_streak_days"], 2)
        self.assertIn("2-day streak", status["message"])

    def test_streak_breaks_on_missed_day(self) -> None:
        user = self.service.create_user("Alex")
        habit = self.service.add_habit(user["id"], "Workout")

        self.service.check_in(habit["id"], "2026-04-08")
        self.service.check_in(habit["id"], "2026-04-10")

        status = self.service.daily_status(user["id"], "2026-04-10")
        self.assertEqual(status["streak"]["current_streak_days"], 1)

    def test_no_habits_has_zero_streak_and_prompt_message(self) -> None:
        user = self.service.create_user("Alex")
        status = self.service.daily_status(user["id"], "2026-04-10")
        self.assertEqual(status["streak"]["current_streak_days"], 0)
        self.assertEqual(status["summary"]["total_habits"], 0)
        self.assertIn("Add your first habit", status["message"])


if __name__ == "__main__":
    unittest.main()
