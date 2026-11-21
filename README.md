# capalens-ia-check

[![Website](https://img.shields.io/badge/website-capalens.com-0b6fbf)](https://capalens.com)
[![CI](https://github.com/DefineFuture/capalens-ia-check/actions/workflows/ci.yml/badge.svg)](https://github.com/DefineFuture/capalens-ia-check/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab)

**Read-only checks for Intelligent Access (IA) — the MCP servers, APIs, agents and skills that AI connects to.
Evidence for every result, in the spirit of the IAP evidence format. No scores.**

[Website](https://capalens.com) · [IA and IAP](docs/ia-and-iap.md) · [Wiki: ideas](https://github.com/DefineFuture/capalens-ia-check/wiki) · [中文说明](README.zh-CN.md) · [Checks](docs/checks.md) · [GitHub Action](docs/github-action.md) ·
[Monitoring](docs/monitoring.md) · [Report format](docs/report-format.md) · [Methodology](docs/methodology.md) ·
[Related projects: positioning](docs/comparison.md)

`capalens-ia-check` is the small, open-source companion of the **CapaLens** detection engine. It answers one
question about an Intelligent Access (IA), quickly and repeatably: *what can be observed about it right now, against its
own specification?*

```text
$ capalens-ia-check mcp https://mcp.example.com/mcp
  [PASS   ] MCP-003   Handshake returns a JSON-RPC result - initialize answered
  [PASS   ] MCP-004   Negotiated protocol version is a published revision - protocol version 2025-11-25
  [FAIL   ] MCP-009   Tool names follow the naming rules - 1 name(s) outside 1-128 of A-Z a-z 0-9 _ - .
  [REVIEW ] SEC-003   Declared tool annotations agree with the tool text - 1 tool(s): declared hints and
                      tool text disagree (candidates, not observed actions)
  Summary: 15 pass, 1 fail, 1 review, 0 unknown, 1 skip | 7 request(s)
```

## IA and IAP

> **IA — Intelligent Access.** In CapaLens, Intelligent Access means the specific endpoints and access
> capabilities that an AI or LLM application can connect to, invoke or operate: MCP servers, APIs, CLIs, SDKs,
> remote connections, agent skills. "Intelligent" describes the entry point's place in AI workflows — the service
> itself need not contain a model. Being called IA does not mean being tested or safe.
>
> **IAP — Intelligent Access Protocol (draft).** An early proposal by the CapaLens project for a shared data
> language for the capability descriptions, verification evidence and trust assessments of IA. It is not another
> calling protocol and replaces neither MCP nor registries: a registry tells you *what exists*; IAP records *the
> evidence for relying on it* — version, conditions, permissions, test results, check date and evidence source.
> IAP is a project proposal, **not an adopted industry standard and not part of MCP**.

| | IA | IAP |
| --- | --- | --- |
| What it is | the entry points AI uses: MCP, API, CLI, SDK, remote connections, skills, agents | a draft data language for evidence about one IA |
| Question it answers | *through which entry points can an AI use which capabilities?* | *what is this IA, under which conditions, on what evidence?* |
| What capalens-ia-check does with it | checks four kinds of IA material: MCP servers, OpenAPI documents, A2A Agent Cards, Agent Skills | writes machine-check evidence that follows IAP's evidence principles: version and date, `unknown` stays unknown, no composite score (no IAP records yet) |

Read more: [IA and IAP](docs/ia-and-iap.md) ·
[What is Intelligent Access](https://capalens.com/en/guides/what-is-intelligent-access/) ·
[The IAP draft](https://capalens.com/en/guides/iap-protocol-draft/) ·
[IAP evidence format](https://capalens.com/en/guides/iap-evidence-format/)

## Why another checker

* **One tool, four kinds of AI integration.** A remote MCP server, the OpenAPI document behind a tool, an A2A
  Agent Card and an Agent Skill are checked the same way and reported in the same format.
* **Read-only, local-only.** For an MCP server it sends the handshake and the `*/list` requests, one request for
  a method that does not exist, and ends the session. **It never calls a tool**, reads a resource or fetches a
  prompt, and it never sends what it finds to anyone: the security screens are word lists that run on your
  machine.
* **Evidence, not scores.** Every result is `pass`, `fail`, `review`, `unknown` or `skip`, with the message,
  the evidence and the specification it was checked against. `review` means "a human should look at this" —
  a heuristic candidate, never a verdict. There is no score, grade or badge to game.
* **Built for CI and monitoring.** Exit codes, JSON, Markdown and SARIF 2.1.0 output, a GitHub Action, and
  pinning of MCP tool definitions: run it on a schedule and a changed tool description (a "rug pull") becomes a
  review candidate.
* **No dependencies.** The standard library only (PyYAML optional, for YAML OpenAPI documents).

## Install

Python 3.11 or newer.

```bash
pipx install capalens-ia-check            # once published to PyPI
pipx install git+https://github.com/DefineFuture/capalens-ia-check   # from the repository
```

Or use `pip install capalens-ia-check`, `uvx capalens-ia-check`, or the container image (see [Docker](#docker)).
Add `[yaml]` (`pip install "capalens-ia-check[yaml]"`) to read YAML OpenAPI documents.

## Try it in ten seconds

```bash
capalens-ia-check demo
```

`demo` starts a local MCP server on 127.0.0.1 with a well-behaved and a deliberately risky tool set, checks
both, then checks a bundled OpenAPI document, Agent Card and Agent Skill. Nothing leaves your machine. The risky
server shows what failures and review candidates look like: a duplicate tool name, a session id with a space, a
hidden `<IMPORTANT>` instruction to read `~/.ssh/id_rsa`, invisible Unicode, and a tool declared read-only whose
description deletes files.

## Use

```bash
# A remote MCP server (Streamable HTTP). A token is read from an environment variable, never from the command line.
export MCP_TOKEN=...
capalens-ia-check mcp https://mcp.example.com/mcp --bearer-env MCP_TOKEN

# An OpenAPI 3.0/3.1 document, an A2A Agent Card (a base URL reads /.well-known/agent-card.json), an Agent Skill
capalens-ia-check openapi ./openapi.json
capalens-ia-check agent-card https://agents.example.com
capalens-ia-check skill ./skills/release-notes

# Many targets at once, compared with the previous run
capalens-ia-check run capalens-targets.json --baseline last-report.json --json-out report.json
```

Common options:

| Option | Meaning |
| --- | --- |
| `--format text\|json\|markdown\|sarif` | what is printed (default `text`) |
| `--json-out`, `--markdown-out`, `--sarif-out FILE` | also write these files (any combination) |
| `--fail-on fail\|review\|unknown\|never` | exit 1 when a result is at or above this outcome (default `fail`) |
| `--baseline REPORT` | an earlier JSON report: changed MCP tool definitions become `review` (SEC-004) |
| `--timeout`, `--max-requests` | per-request timeout (15 s) and request budget per target (25) |
| `--bearer-env VAR`, `--header 'Name: value'` | credentials; values are sent, never printed or written to a report |
| `-v` | show skipped checks and evidence |

Exit codes: `0` nothing at or above `--fail-on`, `1` something is, `2` usage or input error.

A targets file lists what to check; paths are relative to the file, credentials are named environment
variables ([example](examples/targets-with-mcp.json)):

```json
{
  "defaults": { "timeout": 15, "maxRequests": 25 },
  "targets": [
    { "name": "my-mcp-server", "kind": "mcp", "location": "https://mcp.example.com/mcp", "bearerEnv": "MY_MCP_TOKEN" },
    { "name": "my-api", "kind": "openapi", "location": "openapi.json" },
    { "name": "my-agent", "kind": "agent-card", "location": "https://agents.example.com" },
    { "name": "my-skill", "kind": "skill", "location": "skills/my-skill" }
  ]
}
```

## What is checked

39 checks in three layers — **L0** reachability and transport, **L1** protocol and format, **L3** security
candidates. The full list with references is in [docs/checks.md](docs/checks.md) (`capalens-ia-check checks`).

| Kind | Checks |
| --- | --- |
| MCP server | HTTPS; handshake (`initialize`, or `server/discover` for the stateless 2026-07-28 revision); negotiated version; `serverInfo`; JSON-RPC ids; session id characters; `tools/list`; tool name rules and uniqueness; input schemas; pagination; `-32601` for unknown methods; capabilities match what is served |
| OpenAPI | parses; 3.0/3.1; `info`; operations; unique `operationId`; path parameters declared; internal `$ref`s resolve; security schemes declared; HTTPS servers; responses (3.0) |
| A2A Agent Card | parses; required fields (1.0 and 0.x cards); skills; HTTPS interfaces; security schemes declared |
| Agent Skill | front matter; `name`/`description` limits; name format matches the directory; allowed fields; body size; bundled executables listed (never run) |
| All kinds (L3) | prompt-injection and exfiltration wording; invisible and bidirectional characters; for MCP, tool annotations that disagree with the tool's own text, and changes since a baseline |

## In GitHub Actions

```yaml
- uses: DefineFuture/capalens-ia-check@v0
  with:
    kind: openapi            # mcp | openapi | agent-card | skill | run
    target: openapi.yaml
    fail-on: fail
```

The action writes a Markdown summary to the run page and JSON and SARIF files you can upload to code scanning.
Ready-to-copy workflows: [pull-request check](examples/github/capalens-pr.yml) and
[scheduled monitoring](examples/github/capalens-monitor.yml). Details in [docs/github-action.md](docs/github-action.md).

## Docker

```bash
docker build -t capalens-ia-check .
docker run --rm capalens-ia-check mcp https://mcp.example.com/mcp
docker run --rm -v "$PWD:/work" capalens-ia-check openapi /work/openapi.json
```

## What it does not do

* It does not prove an integration is safe, or unsafe. A `pass` is what these checks observed this time; a
  `review` is a candidate for a human. Read [docs/methodology.md](docs/methodology.md).
* It does not call tools, follow external `$ref`s, verify Agent Card signatures, run skill scripts, or test
  business behaviour. It is not a full conformance suite: for MCP, also run the official
  [conformance tests](https://github.com/modelcontextprotocol/conformance).
* The security screens read English words, not meaning; deceptive text can pass and harmless text can be flagged.

## Relationship to CapaLens

[CapaLens](https://capalens.com) maps AI integrations — MCP servers, APIs, agents, skills — with evidence
about what they are and how they behave. Its detection engine runs a larger, four-layer pipeline with signed,
versioned evidence and human review. `capalens-ia-check` takes a subset of that engine's checks and its shared
heuristics (`action-heuristic/3`, `poisoning-lexicon/0.1`) and makes them easy to run anywhere. Results from
this tool are not CapaLens catalogue results. Learn more at [capalens.com](https://capalens.com).

## Contributing, security, license

* Contributions are welcome — new checks, false-positive reports, documentation: see
  [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).
* Report vulnerabilities privately: [SECURITY.md](SECURITY.md).
* Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). Copyright 2026 南京定义未来科技有限公司
  (Nanjing Define Future Technology Co., Ltd.).
