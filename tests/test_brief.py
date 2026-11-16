import unittest
from datetime import date
from orbitminder.brief import build_brief, format_brief


class BriefTests(unittest.TestCase):
    def test_due_first(self):
        report = build_brief([
            {"name": "Regular", "next_action": "Continue", "priority": 8},
            {"name": "Urgent", "next_action": "Follow up", "priority": 1,
             "status": "waiting", "follow_up_date": "2026-11-16"}
        ], date(2026, 11, 16))
        self.assertEqual(report["top_three"][0][1], "Urgent")
        self.assertEqual(report["waiting"], ["Urgent"])

    def test_unverified_flag(self):
        report = build_brief([{"name": "InboxTend", "next_action": "Check"}], date(2026, 11, 16))
        self.assertIn("Not live-verified", format_brief(report))

    def test_completed_not_prioritized(self):
        report = build_brief([{"name": "Done", "status": "done", "next_action": "Nothing"}],
                             date(2026, 11, 16))
        self.assertFalse(report["top_three"])


if __name__ == "__main__":
    unittest.main()
