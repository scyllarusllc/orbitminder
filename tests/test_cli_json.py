import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orbitminder.cli import main


class JsonCliTests(unittest.TestCase):
    def test_local_json_output_for_dashboard(self):
        with tempfile.TemporaryDirectory() as directory:
            location = Path(directory) / "projects.json"
            location.write_text(json.dumps([
                {"name": "OrbitMinder", "priority": 5,
                 "next_action": "Review open issues", "source_status": "verified"}
            ]), encoding="utf-8")
            output = io.StringIO()
            with patch.object(sys, "argv", [
                "orbitminder", "--data", str(location),
                "--date", "2026-11-16", "--format", "json"
            ]), contextlib.redirect_stdout(output):
                main()
            report = json.loads(output.getvalue())
            self.assertEqual(report["project_count"], 1)
            self.assertEqual(report["date"], "2026-11-16")
            self.assertEqual(report["top_three"][0][1], "OrbitMinder")
            self.assertEqual(report["unverified"], [])

    def test_invalid_format_rejected(self):
        with patch.object(sys, "argv", [
            "orbitminder", "--data", "irrelevant.json", "--format", "xml"
        ]), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main()


if __name__ == "__main__":
    unittest.main()
