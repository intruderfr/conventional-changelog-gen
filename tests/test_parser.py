import unittest

from conventional_changelog.parser import Commit, parse_commit


def _c(subject, body="", sha="abc1234abc1234abc1234abc1234abc1234abcd"):
    return Commit(sha=sha, subject=subject, body=body)


class TestParser(unittest.TestCase):
    def test_basic_feat(self):
        p = parse_commit(_c("feat: add health endpoint"))
        self.assertEqual(p.type, "feat")
        self.assertIsNone(p.scope)
        self.assertEqual(p.description, "add health endpoint")
        self.assertFalse(p.breaking)

    def test_feat_with_scope(self):
        p = parse_commit(_c("feat(api): add /v1/health endpoint"))
        self.assertEqual(p.type, "feat")
        self.assertEqual(p.scope, "api")
        self.assertEqual(p.description, "add /v1/health endpoint")

    def test_fix(self):
        p = parse_commit(_c("fix(db): avoid deadlock"))
        self.assertEqual(p.type, "fix")
        self.assertEqual(p.scope, "db")

    def test_breaking_marker(self):
        p = parse_commit(_c("feat!: drop legacy auth"))
        self.assertTrue(p.breaking)
        self.assertEqual(p.type, "feat")

    def test_breaking_marker_with_scope(self):
        p = parse_commit(_c("perf(api)!: rewrite index lookup"))
        self.assertTrue(p.breaking)
        self.assertEqual(p.scope, "api")

    def test_breaking_footer(self):
        p = parse_commit(
            _c(
                "refactor: restructure config loader",
                body="BREAKING CHANGE: config keys are now lowercase",
            )
        )
        self.assertTrue(p.breaking)
        self.assertEqual(p.breaking_description, "config keys are now lowercase")

    def test_breaking_footer_with_dash(self):
        p = parse_commit(
            _c("refactor: x", body="BREAKING-CHANGE: kaboom")
        )
        self.assertTrue(p.breaking)
        self.assertEqual(p.breaking_description, "kaboom")

    def test_non_conventional_subject(self):
        p = parse_commit(_c("Merge pull request #42 from branch"))
        self.assertEqual(p.type, "other")
        self.assertEqual(p.description, "Merge pull request #42 from branch")
        self.assertFalse(p.breaking)

    def test_short_sha(self):
        p = parse_commit(_c("feat: x"))
        self.assertEqual(len(p.short_sha), 7)

    def test_footer_collection(self):
        body = (
            "Refs: #123\n"
            "Signed-off-by: Example <e@example.com>\n"
        )
        p = parse_commit(_c("fix: y", body=body))
        self.assertIn("Refs: #123", p.footers)
        self.assertTrue(
            any(f.startswith("Signed-off-by") for f in p.footers)
        )

    def test_breaking_footer_multiline(self):
        body = (
            "BREAKING CHANGE: this spans\n"
            "multiple lines for one reason\n"
            "\n"
            "Refs: #42\n"
        )
        p = parse_commit(_c("feat: z", body=body))
        self.assertTrue(p.breaking)
        self.assertIn("multiple lines", p.breaking_description)
        self.assertIn("Refs: #42", p.footers)


if __name__ == "__main__":
    unittest.main()
