import os
import tempfile
import unittest
from pathlib import Path

from logwise.env import find_dotenv, load_dotenv, parse_dotenv_text

from .helpers import clear_managed_env


class TestParseDotenv(unittest.TestCase):
    def test_basic_and_quotes(self):
        d = parse_dotenv_text("A=1\nB=\"x y\"\nC='z'\n")
        self.assertEqual(d, {"A": "1", "B": "x y", "C": "z"})

    def test_comments_and_export(self):
        d = parse_dotenv_text("# full\n  export D=2  \nE=3 # trailing\n")
        self.assertEqual(d, {"D": "2", "E": "3"})

    def test_quoted_hash_kept(self):
        d = parse_dotenv_text('Q="keep # hash"\n')
        self.assertEqual(d, {"Q": "keep # hash"})

    def test_invalid_lines_skipped(self):
        d = parse_dotenv_text("NOEQUALS\n=noname\n9BAD=x\nBAD-KEY=x\nOK=1\n")
        self.assertEqual(d, {"OK": "1"})

    def test_empty_value(self):
        self.assertEqual(parse_dotenv_text("EMPTY=\n"), {"EMPTY": ""})


class TestFindDotenv(unittest.TestCase):
    def test_walks_upward(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("A=1\n")
            deep = root / "a" / "b"
            deep.mkdir(parents=True)
            self.assertEqual(find_dotenv(deep), root / ".env")

    def test_none_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(find_dotenv(Path(tmp)))


class TestLoadDotenv(unittest.TestCase):
    def setUp(self):
        clear_managed_env(self)

    def test_loads_and_returns_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / ".env"
            p.write_text("LOADTEST_A=hello\n")
            self.assertEqual(load_dotenv(p), p)
            self.assertEqual(os.environ["LOADTEST_A"], "hello")

    def test_exports_win_over_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / ".env"
            p.write_text("LOADTEST_B=from-file\n")
            os.environ["LOADTEST_B"] = "from-export"
            load_dotenv(p)
            self.assertEqual(os.environ["LOADTEST_B"], "from-export")

    def test_missing_explicit_file_warns(self):
        os.environ["LOGWISE_ENV_FILE"] = str(Path(tempfile.gettempdir()) / "logwise-no-such-env")
        self.assertIsNone(load_dotenv())

    def test_explicit_override_var(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "custom.env"
            p.write_text("LOADTEST_C=1\n")
            os.environ["LOGWISE_ENV_FILE"] = str(p)
            self.assertEqual(load_dotenv(), p)
            self.assertEqual(os.environ["LOADTEST_C"], "1")


if __name__ == "__main__":
    unittest.main()
