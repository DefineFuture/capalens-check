# GitHub Action

```yaml
- uses: DefineFuture/capalens-check@v0
  with:
    kind: openapi
    target: openapi.yaml
```

The action installs capalens-check from its own checkout (no package index needed for the tool itself; PyYAML
is installed for YAML documents), runs it, writes a Markdown summary to the run page, and leaves a JSON and a
SARIF report in the workspace.

## Inputs

| Input | Default | Meaning |
| --- | --- | --- |
| `kind` | — | `mcp`, `openapi`, `agent-card`, `skill`, or `run` (a targets file) |
| `target` | — | URL, file, skill directory, or targets file |
| `fail-on` | `fail` | fail the step at or above `fail`, `review`, `unknown`; `never` to only report |
| `baseline` | — | an earlier JSON report; ignored when the file does not exist (first run) |
| `bearer-token` | — | sent as `Authorization: Bearer ...` for a single target; pass a secret |
| `json-file` | `capalens-check.json` | JSON report path |
| `sarif-file` | `capalens-check.sarif` | SARIF report path |
| `python-version` | `3.12` | Python used to run the tool |

Outputs: `json-file`, `sarif-file`, `exit-code` (`0`, `1`, `2`).

The Markdown summary goes to `$GITHUB_STEP_SUMMARY` whenever capalens-check runs inside GitHub Actions (also
when you call the CLI directly in a step); set `CAPALENS_STEP_SUMMARY=0` to turn it off.

## Credentials

For a single target, pass a secret: `bearer-token: ${{ secrets.MCP_TOKEN }}`. For a targets file, name an
environment variable per target (`"bearerEnv": "MY_MCP_TOKEN"`, or `"headersEnv": {"X-Api-Key": "MY_KEY"}`)
and set it on the step:

```yaml
- uses: DefineFuture/capalens-check@v0
  with:
    kind: run
    target: capalens-targets.json
  env:
    MY_MCP_TOKEN: ${{ secrets.MY_MCP_TOKEN }}
```

Values are sent to the target only; they never appear in the summary or the reports. The action passes all
inputs to its script through environment variables, never by expanding them inside the script.

## Code scanning

```yaml
permissions:
  security-events: write
steps:
  - uses: DefineFuture/capalens-check@v0
    with: { kind: run, target: capalens-targets.json, sarif-file: capalens.sarif }
  - uses: github/codeql-action/upload-sarif@v4
    if: always()
    with: { sarif_file: capalens.sarif, category: capalens-check }
```

SARIF results carry the target as their location: a repository path for files, the URL for remote targets.
Code scanning shows file results best; for remote MCP servers, the run summary and the JSON artifact are the
better view.

## Monitoring on a schedule

See [monitoring.md](monitoring.md) and the ready workflow
[examples/github/capalens-monitor.yml](../examples/github/capalens-monitor.yml).

## Versions

Use the major tag (`@v0`) for updates within a major version, or a full commit SHA to pin exactly (recommended
for security-sensitive workflows; Dependabot can keep SHAs current).
