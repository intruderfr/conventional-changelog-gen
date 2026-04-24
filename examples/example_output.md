# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0](https://github.com/example/sample-app/compare/v1.2.0...v1.3.0) — 2026-04-24

### Breaking Changes

- **perf**: rewrite index lookup (2x throughput) — index schema has changed, see MIGRATION.md ([abc1234](https://github.com/example/sample-app/commit/abc1234abc1234abc1234abc1234abc1234abcd))

### Features

- **api**: add /v1/health endpoint ([def5678](https://github.com/example/sample-app/commit/def5678def5678def5678def5678def5678defa))
- **auth**: support passwordless magic links ([1112223](https://github.com/example/sample-app/commit/1112223111222311122231112223111222311122))

### Bug Fixes

- **db**: avoid deadlock on concurrent writes ([aaa9999](https://github.com/example/sample-app/commit/aaa9999aaa9999aaa9999aaa9999aaa9999aaa9))
- **web**: correct focus trap in modal ([bbb8888](https://github.com/example/sample-app/commit/bbb8888bbb8888bbb8888bbb8888bbb8888bbb8))

### Documentation

- **readme**: clarify install instructions for Windows ([ccc7777](https://github.com/example/sample-app/commit/ccc7777ccc7777ccc7777ccc7777ccc7777ccc7))

## [1.2.0](https://github.com/example/sample-app/compare/v1.1.0...v1.2.0) — 2026-03-12

### Features

- **billing**: add usage-based invoicing ([fff4444](https://github.com/example/sample-app/commit/fff4444fff4444fff4444fff4444fff4444fff4))

### Bug Fixes

- **web**: prevent double-submit on slow networks ([eee3333](https://github.com/example/sample-app/commit/eee3333eee3333eee3333eee3333eee3333eee3))
