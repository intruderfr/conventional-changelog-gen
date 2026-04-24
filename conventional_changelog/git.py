"""Thin wrapper around the ``git`` CLI.

Kept small on purpose: we only shell out for the operations we actually
need and we don't add a hard dependency on libgit. Each function raises
``GitError`` on a non-zero exit.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .parser import Commit

# Unit separator + record separator — unlikely to appear in commit text.
_UNIT = "\x1f"
_RECORD = "\x1e"


class GitError(RuntimeError):
    """Raised when a git invocation fails."""


def _run(args: List[str], cwd: Optional[str] = None) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitError("`git` is not installed or not on PATH") from exc

    if proc.returncode != 0:
        stderr = proc.stderr.strip() or proc.stdout.strip()
        raise GitError(f"git {' '.join(args)} failed: {stderr}")
    return proc.stdout


def is_git_repo(path: Optional[str] = None) -> bool:
    """Return True if ``path`` (default: cwd) is inside a git work tree."""
    try:
        out = _run(["rev-parse", "--is-inside-work-tree"], cwd=path)
    except GitError:
        return False
    return out.strip() == "true"


def list_tags(path: Optional[str] = None) -> List[str]:
    """Return tags sorted by creation date (most recent first)."""
    out = _run(
        ["for-each-ref", "--sort=-creatordate", "--format=%(refname:short)", "refs/tags"],
        cwd=path,
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def latest_tag(path: Optional[str] = None) -> Optional[str]:
    tags = list_tags(path)
    return tags[0] if tags else None


def tag_exists(ref: str, path: Optional[str] = None) -> bool:
    try:
        _run(["rev-parse", "--verify", f"refs/tags/{ref}"], cwd=path)
    except GitError:
        return False
    return True


def list_commits(
    from_ref: Optional[str],
    to_ref: str = "HEAD",
    path: Optional[str] = None,
) -> List[Commit]:
    """Return commits in ``from_ref..to_ref`` (exclusive of from_ref).

    If ``from_ref`` is None, returns all commits reachable from ``to_ref``.
    Commits are returned in chronological order (oldest first) which
    matches ``git log --reverse``.
    """

    if from_ref:
        rev_range = f"{from_ref}..{to_ref}"
    else:
        rev_range = to_ref

    fmt = _UNIT.join(["%H", "%s", "%b", "%an", "%ad"]) + _RECORD
    args = ["log", "--reverse", f"--pretty=format:{fmt}", "--date=iso-strict", rev_range]
    out = _run(args, cwd=path)

    commits: List[Commit] = []
    for raw in out.split(_RECORD):
        raw = raw.strip("\n")
        if not raw.strip():
            continue
        parts = raw.split(_UNIT)
        # Be tolerant: %b can be empty, which still yields 5 parts.
        if len(parts) < 5:
            parts += [""] * (5 - len(parts))
        sha, subject, body, author, date = parts[:5]
        commits.append(
            Commit(
                sha=sha.strip(),
                subject=subject.strip(),
                body=body.strip(),
                author=author.strip(),
                date=date.strip(),
            )
        )
    return commits


@dataclass
class RemoteInfo:
    host: str       # "github.com"
    owner: str
    repo: str

    @property
    def web_url(self) -> str:
        return f"https://{self.host}/{self.owner}/{self.repo}"


_REMOTE_PATTERNS = [
    # git@github.com:owner/repo.git
    re.compile(r"^git@(?P<host>[^:]+):(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$"),
    # https://github.com/owner/repo(.git)
    re.compile(r"^https?://(?P<host>[^/]+)/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"),
    # ssh://git@github.com/owner/repo.git
    re.compile(r"^ssh://git@(?P<host>[^/]+)/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$"),
]


def parse_remote_url(url: str) -> Optional[RemoteInfo]:
    url = (url or "").strip()
    for pat in _REMOTE_PATTERNS:
        m = pat.match(url)
        if m:
            return RemoteInfo(
                host=m.group("host"),
                owner=m.group("owner"),
                repo=m.group("repo"),
            )
    return None


def detect_remote(path: Optional[str] = None) -> Optional[RemoteInfo]:
    """Best-effort detection of the ``origin`` remote URL."""
    try:
        url = _run(["config", "--get", "remote.origin.url"], cwd=path).strip()
    except GitError:
        return None
    return parse_remote_url(url)


_SEMVER_TAG = re.compile(r"^v?\d+\.\d+\.\d+")


def is_release_tag(name: str) -> bool:
    """Return True if ``name`` looks like a release tag (semver-ish)."""
    return bool(_SEMVER_TAG.match(name))


def guess_range(
    from_ref: Optional[str],
    to_ref: str,
    include_unreleased: bool,
    path: Optional[str] = None,
) -> Tuple[Optional[str], str]:
    """Resolve the effective (from, to) range based on flags and tags."""

    if from_ref is None:
        tags = [t for t in list_tags(path) if is_release_tag(t)]
        if include_unreleased and tags:
            # Latest tag to HEAD
            return tags[0], to_ref
        # Pick second-most-recent tag (so we describe the last release)
        if len(tags) >= 2:
            return tags[1], tags[0] if to_ref == "HEAD" else to_ref
        if len(tags) == 1:
            return None, tags[0] if to_ref == "HEAD" else to_ref
        return None, to_ref
    return from_ref, to_ref
