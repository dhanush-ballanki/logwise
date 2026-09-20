import unittest

from logwise.rules import ERROR_RULES, apply_rules

from .helpers import clear_managed_env


def make_log(stderr="", exit_code=1):
    return {"command": "cmd", "stderr": stderr, "exit_code": exit_code}


class TestRules(unittest.TestCase):
    def setUp(self):
        clear_managed_env(self)

    def test_non_zero_exit_matches(self):
        issues = apply_rules(make_log(exit_code=2))
        self.assertIn("non_zero_exit", [i["rule_id"] for i in issues])

    def test_zero_exit_no_match(self):
        issues = apply_rules(make_log(stderr="", exit_code=0))
        self.assertEqual(issues, [])

    def test_permission_denied_case_insensitive(self):
        issues = apply_rules(make_log("bash: x: Permission DENIED"))
        self.assertIn("permission_denied", [i["rule_id"] for i in issues])

    def test_file_not_found(self):
        issues = apply_rules(make_log("ls: cannot access '/x': No such file or directory"))
        self.assertIn("file_not_found", [i["rule_id"] for i in issues])

    def test_multiple_rules_stack(self):
        issues = apply_rules(make_log("x: No such file or directory", exit_code=2))
        self.assertEqual(
            sorted(i["rule_id"] for i in issues),
            ["file_not_found", "non_zero_exit"],
        )

    def test_issue_shape(self):
        (issue,) = [
            i
            for i in apply_rules(make_log("permission denied"))
            if i["rule_id"] == "permission_denied"
        ]
        self.assertIn("description", issue)
        self.assertIn("root_cause", issue)
        self.assertIn("fixes", issue)

    def test_registry_unique_ids(self):
        ids = [r["id"] for r in ERROR_RULES]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
