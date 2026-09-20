import os
import tempfile
import time
import unittest
from pathlib import Path

from logwise.analyze import prune_logs

from .helpers import clear_managed_env


def make_logs(tmp, count, age_days=0):
    names = []
    for i in range(count):
        name = f"log_{i:03d}.json"
        p = Path(tmp) / name
        p.write_text("{}")
        if age_days:
            old = time.time() - age_days * 86400
            os.utime(p, (old, old))
        names.append(name)
    return names


class TestPrune(unittest.TestCase):
    def setUp(self):
        clear_managed_env(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["LOGWISE_LOG_DIR"] = self.tmp.name

    def names(self):
        return sorted(p.name for p in Path(self.tmp.name).glob("*.json"))

    def test_both_none_deletes_nothing(self):
        make_logs(self.tmp.name, 3)
        result = prune_logs()
        self.assertEqual(result["deleted"], [])
        self.assertEqual(result["kept"], 3)

    def test_keep_newest(self):
        make_logs(self.tmp.name, 5)
        result = prune_logs(keep=2)
        self.assertEqual(len(result["deleted"]), 3)
        self.assertEqual(self.names(), ["log_003.json", "log_004.json"])
        self.assertEqual(result["kept"], 2)

    def test_keep_zero_deletes_all(self):
        make_logs(self.tmp.name, 2)
        result = prune_logs(keep=0)
        self.assertEqual(len(result["deleted"]), 2)

    def test_older_than(self):
        make_logs(self.tmp.name, 2, age_days=10)
        make_logs(self.tmp.name, 0)  # none fresh; add fresh below
        fresh = Path(self.tmp.name) / "log_fresh.json"
        fresh.write_text("{}")
        result = prune_logs(keep=None, older_than_days=5)
        self.assertEqual(len(result["deleted"]), 2)
        self.assertEqual(self.names(), ["log_fresh.json"])

    def test_dry_run_deletes_nothing(self):
        make_logs(self.tmp.name, 4)
        result = prune_logs(keep=1, dry_run=True)
        self.assertEqual(len(result["doomed"]), 3)
        self.assertEqual(result["deleted"], [])
        self.assertEqual(len(self.names()), 4)

    def test_non_json_ignored(self):
        make_logs(self.tmp.name, 1)
        (Path(self.tmp.name) / "notes.txt").write_text("x")
        result = prune_logs(keep=0)
        self.assertEqual(len(result["deleted"]), 1)
        self.assertTrue((Path(self.tmp.name) / "notes.txt").exists())


if __name__ == "__main__":
    unittest.main()
