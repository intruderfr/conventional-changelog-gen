import unittest

from conventional_changelog.parser import Commit, parse_commit
from conventional_changelog.generator import (
    CHANGELOG_PREAMBLE,
    ReleaseOptions,
    merge_into_changelog,
    render_release,
)


def _p(subject, body="", sha="abc1234abc1234abc1234abc1234abc1234abcd"):
    return parse_commit(Commit(sha=sha, subject=subject, body=body))


class TestRenderRelease(unittest.TestCase):
    def test_empty_returns_blank(self):
        out = render_release(
            [],
            ReleaseOptions(version_name="v1.0.0", date="2026-01-01"),
        )
        self.assertEqual(out, "")

    def test_basic_render(self):
        commits = [
            _p("feat(api): add health endpoint", sha="1" * 40),
            _p("fix(db): avoid deadlock", sha="2" * 40),
            _p("chore: tidy imports", sha="3" * 40),
        ]
        out = render_release(
            commits,
            ReleaseOptions(version_name="v1.0.0", date="2026-01-01"),
        )
        self.assertIn("## v1.0.0 — 2026-01-01", out)
        self.assertIn("### Features", out)
        self.assertIn("### Bug Fixes", out)
        # chore is internal: should not show up by default
        self.assertNotIn("tidy imports", out)

    def test_include_internal(self):
        commits = [
            _p("feat: new thing", sha="1" * 40),
            _p("chore: tidy imports", sha="2" * 40),
        ]
        out = render_release(
            commits,
            ReleaseOptions(
                version_name="v1.0.0",
                date="2026-01-01",
                include_internal=True,
            ),
        )
        self.assertIn("### Chores", out)
        self.assertIn("tidy imports", out)

    def test_breaking_section_emitted_first(self):
        commits = [
            _p("feat: normal", sha="1" * 40),
            _p("perf!: rewrite index lookup", sha="2" * 40),
        ]
        out = render_release(
            commits,
            ReleaseOptions(version_name="v1.0.0", date="2026-01-01"),
        )
        breaking_idx = out.index("### Breaking Changes")
        features_idx = out.index("### Features")
        self.assertLess(breaking_idx, features_idx)

    def test_breaking_footer_text_included(self):
        commits = [
            _p(
                "refactor: restructure loader",
                body="BREAKING CHANGE: config keys are now lowercase",
                sha="1" * 40,
            ),
        ]
        out = render_release(
            commits,
            ReleaseOptions(version_name="v1.0.0", date="2026-01-01"),
        )
        self.assertIn("config keys are now lowercase", out)

    def test_repo_url_produces_links(self):
        commits = [_p("feat: x", sha="a" * 40)]
        out = render_release(
            commits,
            ReleaseOptions(
                version_name="v1.0.0",
                date="2026-01-01",
                repo_url="https://github.com/o/r",
                from_ref="v0.9.0",
                to_ref="v1.0.0",
            ),
        )
        self.assertIn("https://github.com/o/r/compare/v0.9.0...v1.0.0", out)
        self.assertIn("https://github.com/o/r/commit/" + "a" * 40, out)


class TestMerge(unittest.TestCase):
    def _section(self, name):
        commits = [_p("feat: x", sha="b" * 40)]
        return render_release(
            commits,
            ReleaseOptions(version_name=name, date="2026-01-01"),
        )

    def test_empty_existing_gets_preamble(self):
        new = self._section("v1.0.0")
        merged = merge_into_changelog("", new)
        self.assertTrue(merged.startswith(CHANGELOG_PREAMBLE))
        self.assertIn("## v1.0.0", merged)

    def test_prepends_above_existing_release(self):
        existing = CHANGELOG_PREAMBLE + "## v0.9.0 — 2026-01-01\n\n### Features\n\n- **x**: old\n"
        new = self._section("v1.0.0")
        merged = merge_into_changelog(existing, new)
        # v1.0.0 must appear before v0.9.0
        self.assertLess(merged.index("## v1.0.0"), merged.index("## v0.9.0"))

    def test_replaces_existing_duplicate(self):
        new_first = self._section("v1.0.0")
        merged = merge_into_changelog(CHANGELOG_PREAMBLE, new_first)
        # Render a different "v1.0.0" and merge again — old block should
        # be replaced, not duplicated.
        commits = [_p("fix: y", sha="c" * 40)]
        new_second = render_release(
            commits,
            ReleaseOptions(version_name="v1.0.0", date="2026-02-02"),
        )
        merged2 = merge_into_changelog(merged, new_second)
        self.assertEqual(merged2.count("## v1.0.0"), 1)
        self.assertIn("2026-02-02", merged2)
        self.assertIn("Bug Fixes", merged2)
        self.assertIn("- y", merged2)

    def test_merge_with_preamble_no_releases(self):
        merged = merge_into_changelog(CHANGELOG_PREAMBLE, self._section("v1.0.0"))
        self.assertIn(CHANGELOG_PREAMBLE.strip(), merged)
        self.assertIn("## v1.0.0", merged)


if __name__ == "__main__":
    unittest.main()
