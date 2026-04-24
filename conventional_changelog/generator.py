"""Markdown rendering and changelog merging.

Turns a list of ``ParsedCommit`` objects into a release section, and
merges that section into an existing ``CHANGELOG.md`` without clobbering
prior entries.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from .parser import ParsedCommit

# Default visible section mapping. Types not listed here (chore, style,
# test, other, ...) are considered internal and hidden by default.
DEFAULT_SECTIONS: Dict[str, str] = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "perf": "Performance",
    "refactor": "Code Refactoring",
    "docs": "Documentation",
    "build": "Build System",
    "ci": "Continuous Integration",
    "revert": "Reverts",
}

# Stable order used when rendering sections.
SECTION_ORDER: List[str] = [
    "feat",
    "fix",
    "perf",
    "refactor",
    "docs",
    "build",
    "ci",
    "revert",
]

# Internal types shown only with --include-internal.
INTERNAL_SECTIONS: Dict[str, str] = {
    "chore": "Chores",
    "style": "Styling",
    "test": "Tests",
    "other": "Other Changes",
}

INTERNAL_ORDER: List[str] = ["chore", "style", "test", "other"]


@dataclass
class ReleaseOptions:
    version_name: str
    date: str
    repo_url: Optional[str] = None
    from_ref: Optional[str] = None
    to_ref: Optional[str] = None
    include_internal: bool = False


def today_iso() -> str:
    return _dt.date.today().isoformat()


def _commit_link(commit: ParsedCommit, repo_url: Optional[str]) -> str:
    sha = commit.short_sha
    if not sha:
        return ""
    if repo_url:
        return f" ([{sha}]({repo_url}/commit/{commit.raw.sha}))"
    return f" ({sha})"


def _format_entry(commit: ParsedCommit, repo_url: Optional[str]) -> str:
    scope_prefix = f"**{commit.scope}**: " if commit.scope else ""
    desc = commit.description.rstrip(".")
    suffix = _commit_link(commit, repo_url)
    line = f"- {scope_prefix}{desc}{suffix}"
    return line


def _format_breaking_entry(commit: ParsedCommit, repo_url: Optional[str]) -> str:
    scope_prefix = f"**{commit.scope}**: " if commit.scope else ""
    if commit.type and commit.type != "other":
        scope_prefix = f"**{commit.type}**: " if not commit.scope else (
            f"**{commit.type}({commit.scope})**: "
        )
    desc = commit.description.rstrip(".")
    if commit.breaking_description:
        body = f"{desc} — {commit.breaking_description.rstrip('.')}"
    else:
        body = desc
    suffix = _commit_link(commit, repo_url)
    return f"- {scope_prefix}{body}{suffix}"


def _release_header(opts: ReleaseOptions) -> str:
    name = opts.version_name
    repo = opts.repo_url
    if repo and opts.from_ref and opts.to_ref:
        link = f"{repo}/compare/{opts.from_ref}...{opts.to_ref}"
        heading = f"[{name}]({link})"
    else:
        heading = name
    return f"## {heading} — {opts.date}"


def render_release(
    commits: List[ParsedCommit],
    opts: ReleaseOptions,
    sections: Optional[Dict[str, str]] = None,
) -> str:
    """Render a single release section as markdown.

    Returns an empty string if there are no visible commits.
    """

    visible_map = dict(sections) if sections else dict(DEFAULT_SECTIONS)
    order = list(SECTION_ORDER)
    if opts.include_internal:
        visible_map.update(INTERNAL_SECTIONS)
        order = order + INTERNAL_ORDER

    breaking = [c for c in commits if c.breaking]
    by_type: Dict[str, List[ParsedCommit]] = {t: [] for t in visible_map}
    for c in commits:
        if c.type in by_type:
            by_type[c.type].append(c)

    # Nothing visible AND no breaking changes? Bail out.
    if not breaking and not any(by_type.values()):
        return ""

    lines: List[str] = [_release_header(opts), ""]

    if breaking:
        lines.append("### Breaking Changes")
        lines.append("")
        for c in breaking:
            lines.append(_format_breaking_entry(c, opts.repo_url))
        lines.append("")

    for t in order:
        bucket = by_type.get(t, [])
        if not bucket:
            continue
        lines.append(f"### {visible_map[t]}")
        lines.append("")
        for c in bucket:
            lines.append(_format_entry(c, opts.repo_url))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


CHANGELOG_PREAMBLE = (
    "# Changelog\n\n"
    "All notable changes to this project will be documented in this file.\n\n"
    "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),\n"
    "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n\n"
)


_HEADING_RE = re.compile(r"^##\s+", re.MULTILINE)


def merge_into_changelog(existing: str, new_section: str) -> str:
    """Insert ``new_section`` above the first existing release entry.

    - If there is no existing changelog content, prepend the standard
      Keep-a-Changelog preamble.
    - If there is a preamble but no prior releases, append after it.
    - If there are prior releases, insert the new section just before
      the first ``## `` heading.
    - If the new version already exists, its previous block is replaced.
    """

    new_section = new_section.rstrip() + "\n"

    if not existing.strip():
        return CHANGELOG_PREAMBLE + new_section

    # Detect duplicate version heading and, if present, drop the old block.
    first_new_heading_match = re.match(r"^##\s+(.+?)\n", new_section)
    if first_new_heading_match:
        new_heading = first_new_heading_match.group(0).strip()
        existing = _drop_existing_block(existing, new_heading)

    match = _HEADING_RE.search(existing)
    if not match:
        # No releases yet, just append after the preamble.
        sep = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
        return existing + sep + new_section

    head = existing[: match.start()]
    tail = existing[match.start() :]

    if not head.endswith("\n\n"):
        head = head.rstrip("\n") + "\n\n"

    return head + new_section + "\n" + tail


def _drop_existing_block(existing: str, heading_line: str) -> str:
    """If ``heading_line`` is present, remove it and its block.

    A block runs until the next ``## `` heading or end of file.
    """

    # We only want to match the same version heading regardless of the
    # date or link form. Extract just the version token.
    m = re.match(r"##\s+(?:\[(?P<v>[^\]]+)\]\([^)]+\)|(?P<v2>\S+))", heading_line)
    token = (m.group("v") or m.group("v2")) if m else None
    if not token:
        return existing

    pat = re.compile(
        r"(^##\s+(?:\[" + re.escape(token) + r"\]\([^)]+\)|" + re.escape(token) + r")[^\n]*\n)"
        r"(.*?)"
        r"(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    return pat.sub("", existing)
