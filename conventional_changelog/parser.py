"""Conventional Commits parser.

Parses a raw commit (subject + body + metadata) into a structured
``ParsedCommit``. Lenient by design: a commit that does not follow
Conventional Commits will still parse — it just gets type="other" and
is filtered out of the default changelog unless ``include_internal`` is
set.

Spec reference: https://www.conventionalcommits.org/en/v1.0.0/
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

# Header pattern:  type(scope)!: subject
#   type   = [a-z]+  (conventional types are lowercase)
#   scope  = optional, wrapped in parens, may contain any non-paren char
#   !      = optional, marks a breaking change
_HEADER_RE = re.compile(
    r"""
    ^
    (?P<type>[a-zA-Z][a-zA-Z0-9_-]*)      # type
    (?:\((?P<scope>[^)]+)\))?              # optional (scope)
    (?P<breaking>!)?                       # optional !
    :\s+                                   # colon + space
    (?P<subject>.+?)                       # subject line (non-greedy)
    \s*$
    """,
    re.VERBOSE,
)


@dataclass
class Commit:
    """A raw commit as returned by the git layer."""

    sha: str
    subject: str
    body: str = ""
    author: str = ""
    date: str = ""

    @property
    def short_sha(self) -> str:
        return self.sha[:7] if self.sha else ""

    @property
    def full_message(self) -> str:
        if not self.body:
            return self.subject
        return f"{self.subject}\n\n{self.body}"


@dataclass
class ParsedCommit:
    """A commit after Conventional Commit parsing."""

    raw: Commit
    type: str               # "feat", "fix", ... or "other" if unparseable
    scope: Optional[str]    # optional scope, e.g. "api" in "feat(api): ..."
    description: str        # the subject line with the type/scope stripped
    breaking: bool          # True if `!` marker OR BREAKING CHANGE footer
    breaking_description: Optional[str] = None
    footers: List[str] = field(default_factory=list)

    @property
    def short_sha(self) -> str:
        return self.raw.short_sha


def parse_commit(commit: Commit) -> ParsedCommit:
    """Parse a raw ``Commit`` into a ``ParsedCommit``.

    A non-conventional subject yields ``type="other"``, ``scope=None``,
    and ``description`` equal to the full subject. That keeps the
    pipeline robust against messy history.
    """

    subject = commit.subject.strip()
    body = (commit.body or "").strip()

    footers: List[str] = []
    breaking_description: Optional[str] = None

    # BREAKING CHANGE footer detection: scan each line of the body.
    # The spec allows "BREAKING CHANGE:" or "BREAKING-CHANGE:".
    # Anything after the colon (and continuation lines) is the description.
    if body:
        lines = body.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            m = re.match(
                r"^(BREAKING[ -]CHANGE)\s*:\s*(.*)$",
                line,
                re.IGNORECASE,
            )
            if m:
                parts = [m.group(2).strip()]
                j = i + 1
                while j < len(lines) and lines[j].strip() and not re.match(
                    r"^[A-Za-z][A-Za-z0-9-]*\s*:\s", lines[j]
                ):
                    parts.append(lines[j].strip())
                    j += 1
                breaking_description = " ".join(p for p in parts if p).strip()
                footers.append(f"BREAKING CHANGE: {breaking_description}")
                i = j
                continue
            # Generic footer like "Refs: #123" / "Signed-off-by: ..."
            if re.match(r"^[A-Za-z][A-Za-z0-9-]*\s*:\s", line):
                footers.append(line.strip())
            i += 1

    header = _HEADER_RE.match(subject)
    if header:
        ctype = header.group("type").lower()
        scope = header.group("scope")
        description = header.group("subject").strip()
        breaking_marker = bool(header.group("breaking"))
        breaking = breaking_marker or breaking_description is not None
        return ParsedCommit(
            raw=commit,
            type=ctype,
            scope=scope,
            description=description,
            breaking=breaking,
            breaking_description=breaking_description,
            footers=footers,
        )

    # Non-conventional: preserve the full subject.
    return ParsedCommit(
        raw=commit,
        type="other",
        scope=None,
        description=subject,
        breaking=breaking_description is not None,
        breaking_description=breaking_description,
        footers=footers,
    )
