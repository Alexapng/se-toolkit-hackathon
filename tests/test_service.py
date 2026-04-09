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


if __name__ == "__main__":
    unittest.main()
