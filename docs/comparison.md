# Similar projects

capalens-check borrows good ideas from several open-source projects and tries not to duplicate them. Use them
together: each covers ground the others do not.

> Maintainers: descriptions reflect these projects as of 2026 and were written without re-checking each
> repository. Verify names, links and current behaviour before publishing (RELEASING.md, step 3).

| Project | What it is | Where capalens-check differs |
| --- | --- | --- |
| [modelcontextprotocol/inspector](https://github.com/modelcontextprotocol/inspector) | The official interactive tool to connect to an MCP server, list and call its tools | Non-interactive and CI-first; never calls a tool; produces a report with evidence and exit codes |
| [modelcontextprotocol/conformance](https://github.com/modelcontextprotocol/conformance) | The official conformance test scenarios for MCP clients and servers | A small read-only subset that runs against any remote server, plus security screens; run the official suite for full conformance |
| [invariantlabs-ai/mcp-scan](https://github.com/invariantlabs-ai/mcp-scan) | Scans the MCP configurations of local agents (desktop clients, IDEs) for tool poisoning, toxic flows and changed tools ("tool pinning") | Checks remote endpoints and documents rather than local client configs; screens run locally with open word lists (no hosted analysis); pinning through an ordinary JSON report you keep |
| [cisco-ai-defense/mcp-scanner](https://github.com/cisco-ai-defense/mcp-scanner) | MCP server scanning with YARA rules and optional LLM or hosted-API analyzers | No model and no service in the loop; every candidate carries the word and sentence that raised it |
| [a2aproject/a2a-inspector](https://github.com/a2aproject/a2a-inspector) | A web tool to inspect A2A agents, validate Agent Cards and exchange messages | Command line and CI; validates cards from files or URLs without talking to the agent |
| [stoplightio/spectral](https://github.com/stoplightio/spectral) | A flexible JSON/YAML linter with rich OpenAPI rulesets | Ten checks that tool generation relies on, in the same report as MCP, A2A and Skills; use Spectral for full style rules |
| [agentskills/agentskills](https://github.com/agentskills/agentskills) (`skills-ref`) | The Agent Skills specification and its reference validator | The same front-matter rules plus content screening and a listing of bundled executables |
| [ossf/scorecard](https://github.com/ossf/scorecard) | Automated security health checks of open-source repositories, scored 0-10, with a GitHub Action and SARIF | The CI shape is borrowed (Action, SARIF, scheduled runs); the score is not: outcomes and evidence only |

## Why no score

Scorecard-style scores are useful for ranking many repositories by hygiene. For an integration an agent will
call, a single number hides the one property that matters to you (does it authenticate? does its read-only tool
describe deleting data?) and rewards fixing what is cheap to fix. capalens-check reports per-check outcomes with
evidence and leaves the weighing to the reader — the same decision the CapaLens engine made for its catalogue.

## Ideas taken, with thanks

* **Tool pinning** (mcp-scan): hashes of tool definitions to detect changes after approval.
* **Rule ids with references, SARIF output, a GitHub Action, scheduled runs** (Scorecard, Spectral).
* **Testing against the specification text** (the official conformance suite).
