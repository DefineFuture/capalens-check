# Monitoring

A check is a snapshot. Monitoring is the same check on a schedule, compared with the previous snapshot.

## Tool pinning (SEC-004)

Every MCP report records, per tool, the SHA-256 of its definition (canonical JSON of the tool object: name,
title, description, input schema, annotations, everything the server sent). Give an earlier report as
`--baseline` and capalens-ia-check compares:

* **changed** — same name, different definition (a new description is the classic "rug pull": a tool approved
  once that later tells the model something else);
* **added** and **removed** tools.

Any of these makes SEC-004 a `review` candidate with the names in its evidence. Identical definitions pass.
Without a baseline SEC-004 is `skip`.

```bash
capalens-ia-check run capalens-targets.json --json-out today.json              # first run
capalens-ia-check run capalens-targets.json --baseline today.json --json-out tomorrow.json
```

A baseline can be a single-target report or a `run` report; targets are matched by location, then by name.

A changed definition is not bad by itself — servers evolve. The point is that someone looks before trusting the
new text: review the change, then make the new report the baseline.

## On GitHub Actions

[examples/github/capalens-monitor.yml](../examples/github/capalens-monitor.yml) runs daily:

1. restores the previous report from the Actions cache;
2. checks every target in `capalens-targets.json` with that report as the baseline;
3. stores the new report as the next baseline and as an artifact;
4. writes the Markdown summary to the run page and fails the run on any `fail` or `review`.

Turn on notifications for failed scheduled runs (or add a step that opens an issue) to be told.

## Elsewhere

Any scheduler works (cron, a CI system, a container job):

```bash
docker run --rm -v "$PWD:/work" -w /work -e MY_MCP_TOKEN capalens-ia-check \
  run capalens-targets.json --baseline last.json --json-out next.json --fail-on review
```

Keep `next.json` as the next `last.json`. Exit code 1 means something needs a look.

## Budgets

Each MCP target uses about 6-10 requests (handshake, list pages, one unknown-method probe, session end); the
default budget is 25 per target. Be considerate with schedules against servers you do not run.
