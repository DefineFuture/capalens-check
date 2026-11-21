# Similar projects

capalens-ia-check borrows good ideas from several open-source projects and tries not to duplicate them. Use them
together: each covers ground the others do not. (Checked against each repository's description and README on
2026-11-21; these projects move fast.)

| Project | What it is | Where capalens-ia-check differs |
| --- | --- | --- |
| [modelcontextprotocol/inspector](https://github.com/modelcontextprotocol/inspector) | The official developer tool for inspecting MCP servers: web UI, scriptable CLI, terminal UI; connects, lists and calls tools | Read-only by design (never calls a tool, stores no secrets); a pass/fail report against the specification with evidence, SARIF and exit codes; security screens; also OpenAPI, A2A and Skills |
| [modelcontextprotocol/conformance](https://github.com/modelcontextprotocol/conformance) | The official conformance tests for MCP | A small read-only subset that runs against any remote server, plus security screens; run the official suite for full conformance |
| [snyk/agent-scan](https://github.com/snyk/agent-scan) (formerly invariantlabs-ai/mcp-scan) | Discovers the agent components installed on your machine (harnesses, MCP servers, skills) and scans them for prompt injection, sensitive data handling and malware | Checks the endpoints and documents you name instead of discovering local installs; open word lists run locally, nothing is sent to a service; a documented, schema-checked report; no scores |
| [cisco-ai-defense/mcp-scanner](https://github.com/cisco-ai-defense/mcp-scanner) | MCP security scanning with YARA rules, LLM analysis and the Cisco AI Defense API, plus code, package and readiness scanning | No model and no service in the loop; protocol checks next to the security screens; every candidate carries the word and sentence that raised it |
| [a2aproject/a2a-inspector](https://github.com/a2aproject/a2a-inspector) | Validation tools for A2A agents: inspect Agent Cards and exchange messages | Command line and CI; validates cards from files or URLs without talking to the agent |
| [stoplightio/spectral](https://github.com/stoplightio/spectral) | A flexible JSON/YAML linter with rulesets for OpenAPI 2.0/3.0/3.1, Arazzo and AsyncAPI | Ten checks that tool generation relies on, in the same report as MCP, A2A and Skills; use Spectral for full style rules |
| [agentskills/agentskills](https://github.com/agentskills/agentskills) | The Agent Skills specification and documentation, with its reference validator | The same front-matter rules plus content screening and a listing of bundled executables |
| [ossf/scorecard](https://github.com/ossf/scorecard) | Security health metrics for open-source repositories, scored 0-10, with a GitHub Action and SARIF | The CI shape is borrowed (Action, SARIF, scheduled runs); the score is not: outcomes and evidence only |

## Why no score

Scores are useful for ranking many repositories by hygiene. For an integration an agent will call, a single
number hides the one property that matters to you (does it authenticate? does its read-only tool describe
deleting data?) and rewards fixing what is cheap to fix. capalens-ia-check reports per-check outcomes with evidence
and leaves the weighing to the reader — the same decision the CapaLens engine made for its catalogue.

## Ideas taken, with thanks

* **Tool pinning** (mcp-scan, now Snyk Agent Scan): hashes of tool definitions to detect changes after approval.
* **Rule ids with references, SARIF output, a GitHub Action, scheduled runs** (Scorecard, Spectral).
* **Testing against the specification text** (the official conformance suite).
