"""CLI entry point for conventional-changelog-gen."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .generator import (
    ReleaseOptions,
    merge_into_changelog,
    render_release,
    today_iso,
)
from .git import (
    GitError,
    detect_remote,
    guess_range,
    is_git_repo,
    list_commits,
    parse_remote_url,
    tag_exists,
)
from .parser import parse_commit


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="conventional-changelog-gen",
        description=(
            "Generate a CHANGELOG.md section from Conventional Commits in "
            "your git history."
        ),
    )
    p.add_argument(
        "--from",
        dest="from_ref",
        default=None,
        help="Start ref (exclusive). Defaults to the most recent release tag.",
    )
    p.add_argument(
        "--to",
        dest="to_ref",
        default="HEAD",
        help="End ref (inclusive). Defaults to HEAD.",
    )
    p.add_argument(
        "--include-unreleased",
        action="store_true",
        help="Include commits after the latest tag (typically 'Unreleased').",
    )
    p.add_argument(
        "--include-internal",
        action="store_true",
        help="Show chore/style/test/other commits in the changelog.",
    )
    p.add_argument(
        "--output",
        "-o",
        default=None,
        help="Write to this file instead of stdout.",
    )
    p.add_argument(
        "--merge",
        action="store_true",
        help="When --output is set, merge the new section into the file "
             "rather than replacing it.",
    )
    p.add_argument(
        "--repo-url",
        default=None,
        help="Repository web URL used for commit/compare links. "
             "Auto-detected from `origin` if omitted.",
    )
    p.add_argument(
        "--version-name",
        default=None,
        help="Version label to use in the release heading. "
             "Defaults to --to or 'Unreleased' when --include-unreleased is set.",
    )
    p.add_argument(
        "--date",
        default=None,
        help="Release date to put in the heading (YYYY-MM-DD). Defaults to today.",
    )
    p.add_argument(
        "--path",
        default=".",
        help="Path to the git repo (defaults to the current directory).",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return p


def _resolve_repo_url(explicit: Optional[str], path: str) -> Optional[str]:
    if explicit:
        info = parse_remote_url(explicit)
        if info:
            return info.web_url
        return explicit.rstrip("/")
    info = detect_remote(path)
    return info.web_url if info else None


def _resolve_version_name(
    explicit: Optional[str],
    to_ref: str,
    include_unreleased: bool,
) -> str:
    if explicit:
        return explicit
    if to_ref == "HEAD":
        return "Unreleased" if include_unreleased else to_ref
    return to_ref


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    repo_path = args.path
    if not is_git_repo(repo_path):
        print(
            f"error: {os.path.abspath(repo_path)} is not a git repository",
            file=sys.stderr,
        )
        return 2

    # Validate explicit refs up-front for a friendlier error.
    if args.from_ref and not tag_exists(args.from_ref, repo_path):
        # It might still be a branch or a sha, so just try listing.
        try:
            list_commits(args.from_ref, args.to_ref, repo_path)
        except GitError as exc:
            print(f"error: bad --from ref: {exc}", file=sys.stderr)
            return 2

    try:
        from_ref, to_ref = guess_range(
            args.from_ref,
            args.to_ref,
            args.include_unreleased,
            path=repo_path,
        )
        raw_commits = list_commits(from_ref, to_ref, repo_path)
    except GitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parsed = [parse_commit(c) for c in raw_commits]

    repo_url = _resolve_repo_url(args.repo_url, repo_path)
    version_name = _resolve_version_name(
        args.version_name, to_ref, args.include_unreleased
    )

    opts = ReleaseOptions(
        version_name=version_name,
        date=args.date or today_iso(),
        repo_url=repo_url,
        from_ref=from_ref,
        to_ref=to_ref if to_ref != "HEAD" else None,
        include_internal=args.include_internal,
    )

    section = render_release(parsed, opts)
    if not section:
        print(
            "No user-visible commits found in the selected range.",
            file=sys.stderr,
        )
        return 1

    if args.output:
        path = Path(args.output)
        if args.merge and path.exists():
            existing = path.read_text(encoding="utf-8")
            merged = merge_into_changelog(existing, section)
            path.write_text(merged, encoding="utf-8")
        else:
            path.write_text(section, encoding="utf-8")
    else:
        sys.stdout.write(section)

    return 0
