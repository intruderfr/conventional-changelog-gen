"""conventional-changelog-gen.

Generate a CHANGELOG.md from Conventional Commits in git history.
"""

from .parser import Commit, ParsedCommit, parse_commit
from .generator import render_release, merge_into_changelog

__version__ = "0.1.0"

__all__ = [
    "Commit",
    "ParsedCommit",
    "parse_commit",
    "render_release",
    "merge_into_changelog",
    "__version__",
]
