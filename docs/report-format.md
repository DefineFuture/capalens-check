# Report format

JSON reports follow [schemas/report.schema.json](../schemas/report.schema.json) (JSON Schema 2020-12). Two
shapes: one target (`capalens-check.report/1`) and several (`capalens-check.run/1`, from `run` and `demo`).

```json
{
  "format": "capalens-check.report/1",
  "tool": { "name": "capalens-check", "version": "0.1.0" },
  "target": { "kind": "mcp", "location": "https://mcp.example.com/mcp", "name": null },
  "startedAt": "2026-11-21T08:00:00Z",
  "finishedAt": "2026-11-21T08:00:02Z",
  "requests": 7,
  "summary": { "pass": 15, "fail": 1, "review": 1, "unknown": 0, "skip": 1 },
  "results": [
    {
      "id": "SEC-003",
      "title": "Declared tool annotations agree with the tool text",
      "layer": "L3",
      "level": "heuristic",
      "outcome": "review",
      "message": "1 tool(s): declared hints and tool text disagree (candidates, not observed actions)",
      "evidence": {
        "method": "action-heuristic/3",
        "conflicts": [{ "tool": "cleanup", "reasons": ["read-only-declared-but-text-writes-or-executes"],
                        "evidence": [{ "field": "description", "word": "Deletes", "basis": "tool-text-word",
                                       "fragment": "Deletes all cached files" }] }]
      },
      "reference": "https://modelcontextprotocol.io/specification/2025-11-25/server/tools#tool-annotations"
    }
  ],
  "facts": {
    "protocolVersion": "2025-11-25",
    "handshake": "initialize",
    "serverInfo": { "name": "example", "version": "1.2.0" },
    "capabilities": ["prompts", "tools"],
    "toolCount": 4,
    "tools": [{ "name": "get_forecast", "sha256": "sha256:…", "readOnlyHint": true, "labels": ["read"] }]
  },
  "notes": [],
  "disclaimer": "Evidence about one target at one time. No score; ..."
}
```

* `results` holds one entry per check of the target's kind, in catalogue order; `id` values are stable.
* `evidence` differs per check; it never contains credentials, and URLs drop user info and query values.
* `facts` records what was observed (for MCP: the tool definition hashes used by `--baseline`).
* There is deliberately no score field.

## SARIF

`--sarif-out` writes SARIF 2.1.0 with one rule per check used and one result per `fail` or `review`
(`must` fail → `error`, `should` fail and `review` → `warning`). `partialFingerprints.capalensCheck/v1` is stable
per check and target, so code scanning tracks a finding across runs.

## Markdown

`--markdown-out` (and the GitHub step summary) gives a table per target and the evidence of every `fail` and
`review` in a collapsible block.
