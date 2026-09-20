import io
import unittest
from contextlib import redirect_stdout

from rich.console import Console

from logwise import display


def sample_issues():
    return [
        {"rule_id": "r1", "description": "Desc [x].", "root_cause": "Cause.", "fixes": "Do [y]."}
    ]


def sample_ai():
    return {"reason": "R.", "fixes": "1. F", "provider": "openai", "model": "m"}


class TestPlainMode(unittest.TestCase):
    def capture(self, func, *args, **kwargs):
        buf = io.StringIO()
        with redirect_stdout(buf):
            func(*args, **kwargs)
        return buf.getvalue()

    def test_error_header(self):
        out = self.capture(display.error_header, None, 2, True)
        self.assertEqual(out, "Error occurred (exit code: 2)\n")

    def test_analysis_legacy_shape(self):
        out = self.capture(display.analysis, None, "S", sample_issues(), sample_ai(), True)
        self.assertIn("\nAnalysis:\nS\n", out)
        self.assertIn("- Reason: Desc [x]. (Cause.)", out)
        self.assertIn("\nAI Enhanced Analysis:\n", out)

    def test_analysis_no_summary(self):
        out = self.capture(display.analysis, None, "S", [], None, True, show_summary=False)
        self.assertNotIn("Analysis:", out)

    def test_log_table_empty(self):
        out = self.capture(display.log_table, None, [], True)
        self.assertEqual(out, "No logs found.\n")


class TestRichMode(unittest.TestCase):
    def make_console(self):
        return Console(
            record=True, width=80, force_terminal=True, color_system="truecolor", file=io.StringIO()
        )

    def test_rich_widgets_render_without_markup_leak(self):
        c = self.make_console()
        display.error_header(c, 2, plain=False)
        display.stderr_block(c, "err [bold] text", plain=False)
        display.analysis(c, "Summary [x]", sample_issues(), sample_ai(), plain=False)
        display.log_table(c, [{"file": "a.json", "command": "c", "exit_code": 1}], plain=False)
        text = c.export_text()
        self.assertIn("Error occurred", text)
        self.assertIn("err [bold] text", text)  # literal, not swallowed
        self.assertIn("Desc [x].", text)
        self.assertIn("openai / m", text)
        self.assertIn("a.json", text)


if __name__ == "__main__":
    unittest.main()
