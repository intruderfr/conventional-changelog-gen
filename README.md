# conventional-changelog-gen

A small, dependency-light Python CLI that generates a `CHANGELOG.md` from
[Conventional Commits](https://www.conventionalcommits.org/) in your git
history. Built for real release workflows — detects tag ranges, groups
commits by type, surfaces breaking changes, and emits GitHub compare links.

No runtime dependencies beyond the Python standard library. Works with any
repo that uses (or roughly uses) conventional commit messages.

## Features

- Parses `type(scope): subject` headers, optional `!` breaking marker, and
  `BREAKING CHANGE:` footers
- Auto-detects the previous release tag so running it after bumping a new
  tag just works
- Groups commits under human-readable sections (Features, Bug Fixes,
  Performance, Documentation, …) with configurable section mapping
- Emits a **Breaking Changes** block at the top of each release when any
  breaking commits are present
- Adds a GitHub compare link (`https://github.com/OWNER/REPO/compare/X...Y`)
  when a remote is detected, or honors an explicit `--repo-url`
- Merge-safe: prepends new release entries above the existing
  `CHANGELOG.md` so you can re-run it per release without losing history
- Respects `--include-unreleased` so you can preview what will ship before
  cutting the tag

## Install

The tool is a single installable Python package. From a clone:

```bash
pip install .
```

Or run it directly without installing:

```bash
python -m conventional_changelog --help
```

Python 3.9+ is required. Only the standard library is used at runtime.

## Quickstart

Inside a git repo that uses Conventional Commits:

```bash
# Generate a changelog covering the most recent tag to HEAD
conventional-changelog-gen > CHANGELOG.md

# Write and merge into an existing CHANGELOG.md
conventional-changelog-gen --output CHANGELOG.md --merge

# Between two specific refs
conventional-changelog-gen --from v1.2.0 --to v1.3.0

# Include unreleased commits (commits after the latest tag)
conventional-changelog-gen --include-unreleased

# Override the repo URL for compare links
conventional-changelog-gen --repo-url https://github.com/intruderfr/conventional-changelog-gen
```

## Example output

Given a few commits like:

```
feat(api): add /v1/health endpoint
fix(db): avoid deadlock on concurrent writes
perf!: rewrite index lookup (2x throughput)

BREAKING CHANGE: index schema has changed, see MIGRATION.md
```

…the tool produces:

```markdown
## [1.3.0](https://github.com/owner/repo/compare/v1.2.0...v1.3.0) — 2026-04-24

### Breaking Changes

- **perf**: rewrite index lookup (2x throughput) — index schema has changed, see MIGRATION.md ([abc1234](https://github.com/owner/repo/commit/abc1234))

### Features

- **api**: add /v1/health endpoint ([def5678](https://github.com/owner/repo/commit/def5678))

### Bug Fixes

- **db**: avoid deadlock on concurrent writes ([aaa9999](https://github.com/owner/repo/commit/aaa9999))
```

## Commit type mapping

By default, the following types are surfaced in the changelog:

| Type        | Section              |
|-------------|----------------------|
| `feat`      | Features             |
| `fix`       | Bug Fixes            |
| `perf`      | Performance          |
| `refactor`  | Code Refactoring     |
| `docs`      | Documentation        |
| `build`     | Build System         |
| `ci`        | Continuous Integration |
| `revert`    | Reverts              |

`chore`, `style`, and `test` are considered internal and are hidden from
the changelog by default. Use `--include-internal` to show them.

## CLI reference

```
conventional-changelog-gen [--from REF] [--to REF]
                           [--include-unreleased]
                           [--include-internal]
                           [--output FILE]
                           [--merge]
                           [--repo-url URL]
                           [--version-name NAME]
                           [--date DATE]
```

Run `conventional-changelog-gen --help` for the full list.

## Development

```bash
pip install -e .
python -m unittest discover -s tests -v
```

The test suite covers the conventional-commit parser, the section
grouping logic, and the markdown renderer. It does not shell out to git,
so tests run offline in a few hundred milliseconds.

## License

MIT — see [LICENSE](LICENSE).

## Author

**Aslam Ahamed** — Head of IT @ Prestige One Developments, Dubai
[LinkedIn](https://www.linkedin.com/in/aslam-ahamed/)
