import json
import os
import tempfile
import unittest
from pathlib import Path

from logwise.analyze import analyze_log, analyze_log_in_memory, list_logs
from logwise.paths import get_log_dir

from .helpers import clear_managed_env


def make_log(stderr="boom", exit_code=1):
    return {"command": "cmd", "stderr": stderr, "exit_code": exit_code}


class TestAnalyzeInMemory(unittest.TestCase):
    def setUp(self):
        clear_managed_env(self)

    def test_rules_path(self):
        result = analyze_log_in_memory(
            {"command": "c", "stderr": "permission denied", "exit_code": 1}
        )
        self.assertIn("rule-based issue", result["summary"])
        self.assertTrue(result["issues"])
        self.assertNotIn("ai_analysis", result)

    def test_ai_only_missing_key_reports_error(self):
        result = analyze_log_in_memory(make_log(), use_ai=True)
        self.assertIn("AI analysis failed", result["summary"])
        self.assertNotIn("ai_analysis", result)

    def test_ai_only_unknown_provider(self):
        result = analyze_log_in_memory(make_log(), use_ai=True, provider="bogus")
        self.assertIn("Unknown provider", result["summary"])


class TestAnalyzeFiles(unittest.TestCase):
    def setUp(self):
        clear_managed_env(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["LOGWISE_LOG_DIR"] = self.tmp.name
        self.log_path = Path(self.tmp.name) / "log_test.json"
        self.log_path.write_text(json.dumps(make_log()))

    def test_analyze_log_file(self):
        result = analyze_log("log_test.json")
        self.assertIn("rule-based issue", result["summary"])

    def test_analyze_missing_file(self):
        self.assertIn("error", analyze_log("nope.json"))

    def test_list_logs(self):
        self.assertEqual(list_logs(), ["log_test.json"])

    def test_list_logs_missing_dir(self):
        os.environ["LOGWISE_LOG_DIR"] = str(Path(self.tmp.name) / "does-not-exist")
        self.assertEqual(list_logs(), [])


class TestPaths(unittest.TestCase):
    def setUp(self):
        clear_managed_env(self)

    def test_override(self):
        os.environ["LOGWISE_LOG_DIR"] = "~/mylogs"
        self.assertEqual(get_log_dir(), Path.home() / "mylogs")

    def test_default_cwd_based(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                self.assertEqual(get_log_dir(), Path(tmp) / "logs")
            finally:
                os.chdir(old)


if __name__ == "__main__":
    unittest.main()
