# Changelog

All notable changes are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/) (before 1.0, minor versions may change check
behaviour; check ids stay stable).

## [Unreleased]

## [0.1.0] - unreleased

First public version.

### Added

- `capalens-check mcp`: read-only checks of a remote MCP server over Streamable HTTP (JSON and event-stream
  answers; `initialize` handshake for revisions 2024-11-05 to 2025-11-25, `server/discover` for 2026-07-28),
  14 protocol checks, tool definition hashes and drift against a baseline report.
- `capalens-check openapi`, `agent-card`, `skill`: static checks of OpenAPI 3.0/3.1 documents (JSON; YAML with
  the `yaml` extra), A2A Agent Cards (1.0 and 0.x shapes) and Agent Skills.
- Security candidates on every kind: prompt-injection and exfiltration wording, invisible characters, MCP
  annotations that disagree with the tool text (`action-heuristic/3`, shared with the CapaLens engine).
- `capalens-check run` for a targets file, `demo` with a bundled loopback MCP server, `checks` for the catalogue.
- Text, JSON (with a JSON Schema), Markdown and SARIF 2.1.0 output; GitHub step summary; exit codes and
  `--fail-on`.
- GitHub Action, example workflows for pull requests and scheduled monitoring, Dockerfile.
