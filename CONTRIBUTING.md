# Contributing

Thank you for helping. Useful contributions, roughly in order of value:

1. **Wrong results.** A check that fails something correct, or passes something wrong, with a minimal example
   (open a "Wrong result" issue). False positives of the security screens are especially welcome.
2. **New checks** backed by a specification requirement or a well-documented risk (open a "New check" issue
   first so we can agree on the id, level and reference).
3. Documentation, examples and translations.

## Development

```bash
git clone https://github.com/Capalens/capalens-check
cd capalens-check
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev,yaml]"
pytest
ruff check src tests && ruff format --check src tests && mypy
capalens-check demo
```

Tests never leave the machine: MCP behaviour is tested against the bundled demo server and small loopback
servers defined in the tests.

## Rules for checks

* **Read-only.** A check may send metadata requests (`initialize`, `*/list`, an unknown method) and nothing
  that acts: no `tools/call`, `resources/read`, `prompts/get`, no write of any kind.
* **One id, one meaning.** Ids (`MCP-012`) are stable. A check that changes meaning gets a new id; the old one is
  retired, not reused. Add the entry to `src/capalens_check/checks.py` with a reference URL and a one-line
  rationale, then regenerate the catalogue: `capalens-check checks --format markdown > docs/checks.md`.
* **Evidence.** A `fail` or `review` says what was seen (names, fragments, counts) in `evidence`, never a
  credential and never more than needed.
* **No scores.** Do not add a score, grade or weighting, in code or in documentation.
* **Unknown over guessing.** If the check cannot observe the property, the outcome is `unknown`.
* **Tests.** Each check needs a passing and a failing case.

## Pull requests

* One change per pull request; describe the user-visible effect and add a line to `CHANGELOG.md` under
  "Unreleased".
* CI must pass (lint, types, tests on Linux, Windows and macOS, Python 3.11-3.14).
* By contributing you agree that your contribution is licensed under the Apache License 2.0
  ([inbound = outbound](https://www.apache.org/licenses/LICENSE-2.0#contributions)). Please sign off your
  commits (`git commit -s`, the [Developer Certificate of Origin](https://developercertificate.org/)).

## Conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).
