import io
import os
import tempfile
import unittest
from pathlib import Path

from rich.console import Console

from logwise import display
from logwise.capture import capture_and_run
from logwise.paths import ensure_log_dir

from .helpers import clear_managed_env


class TestThemes(unittest.TestCase):
    def test_known_providers(self):
        self.assertEqual(display.provider_color("gemini"), "blue")
        self.assertEqual(display.provider_color("OpenAI"), "green")
        self.assertEqual(display.provider_color("ollama"), "grey62")

    def test_unknown_falls_back(self):
        self.assertEqual(display.provider_color("nope"), "magenta")
        self.assertEqual(display.provider_color(None), "magenta")


class TestProgressAndPrompts(unittest.TestCase):
    def test_ai_progress_plain_is_noop(self):
        c = Console(file=io.StringIO(), force_terminal=False)
        with display.ai_progress(c, "openai", "m", plain=True):
            pass

    def test_prompts_decline_when_not_a_tty(self):
        c = Console(file=io.StringIO(), force_terminal=False)
        self.assertFalse(display.interactive(c))
        self.assertFalse(display.prompt_retry(c))
        self.assertFalse(display.prompt_ai(c))
        self.assertFalse(display.prompt_rerun(c))


class TestEnsureLogDir(unittest.TestCase):
    def setUp(self):
        clear_managed_env(self)

    def test_creates_missing_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "sub" / "logs")
            os.environ["LOGWISE_LOG_DIR"] = target
            self.assertEqual(ensure_log_dir(), Path(target))
            self.assertTrue(Path(target).is_dir())


class TestCaptureReturn(unittest.TestCase):
    def setUp(self):
        clear_managed_env(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["LOGWISE_LOG_DIR"] = self.tmp.name

    def test_success_returns_none(self):
        self.assertIsNone(capture_and_run("echo hi", no_color=True))

    def test_failure_returns_filename(self):
        name = capture_and_run("exit 3", no_color=True)
        self.assertTrue(name.startswith("log_") and name.endswith(".json"))
        self.assertTrue((Path(self.tmp.name) / name).exists())


if __name__ == "__main__":
    unittest.main()
