# Methodology

What a capalens-check result means, and what it does not.

## Principles

1. **Observe, do not act.** Everything sent to a live MCP server is metadata: the handshake, the `*/list`
   requests, one request for a method that does not exist, and a `DELETE` that ends the session the server
   issued. No tool is called, no resource read, no prompt fetched. Documents are read, never executed; external
   `$ref`s are listed, not fetched; skill scripts are listed, never run.
2. **Evidence, not scores.** A result is one of five outcomes with a message and evidence. There is no score,
   because a number hides which property failed, invites optimising for the number, and makes unlike
   integrations look comparable. Counts per outcome are given; their meaning is in the results, not the sum.
3. **A candidate is not a verdict.** The L3 security screens are word lists. Their positive result is
   `review`: a human should look. A `pass` there means "no candidate found by these lists", not "safe".
4. **Unknown is a result.** When something cannot be observed — authentication required, no answer, request
   budget spent — the outcome is `unknown`, never a guess in either direction.
5. **Local only.** Nothing found is sent anywhere. Credentials are sent to the target only, and never written
   to a report; URLs in reports drop user info and query values.
6. **One time, one target.** A report describes one target at one time from one network location. Run it again
   (on a schedule) to see change; compare with `--baseline`.

## Outcomes

| Outcome | Meaning | Blocks with `--fail-on` |
| --- | --- | --- |
| `pass` | the property was observed | never |
| `fail` | the opposite was observed | `fail` (default), `review`, `unknown` |
| `review` | a heuristic candidate for a human | `review`, `unknown` |
| `unknown` | could not be determined | `unknown` |
| `skip` | does not apply to this target | never |

## Levels

Each check has a level: `must` (a requirement of the specification; a fail is an error in SARIF), `should`
(a recommendation or widely relied-on convention; a warning), `heuristic` (a word-list screen; `review` is a
warning) and `info` (a recorded fact).

## Layers

* **L0 — reachability and transport.** Does it answer, over HTTPS?
* **L1 — protocol and format.** Does what it says follow its specification (MCP, OpenAPI, A2A, Agent Skills)?
* **L3 — security candidates.** Is there wording a model would read as an instruction, hidden characters,
  annotations that contradict the text, or a definition that changed since it was approved?

The CapaLens engine also has **L2** (behaviour under approved, read-only business calls) and **L4** (human
review). They need approvals and people, so they are not part of this tool.

## The heuristics

* **Poisoning lexicon** (`poisoning-lexicon/0.1`): instruction overrides ("ignore previous instructions"),
  hidden directives (`<IMPORTANT>`), local secret paths (`~/.ssh`, `.aws/credentials`), exfiltration
  (`webhook.site`, `curl https://...`), credential solicitation and cross-tool manipulation; plus invisible and
  bidirectional Unicode.
* **Action heuristic** (`action-heuristic/3`): compares MCP `readOnlyHint` / `destructiveHint` with the
  actions the tool's own text describes. It handles negation ("does not delete"), exceptions ("unless force is
  true"), field roles (a parameter that "adds review steps to the answer" is not a write) and the object and
  target of add-type verbs ("adds a record to the database" counts; "adds them to the summary" does not). Every
  hit carries its counting basis. It was calibrated on the CapaLens platform's own MCP server and still reads
  words, not meaning.

## Limits

* English word lists. Synonyms are missed ("clearing old files"); a noun can be read as a verb ("Shows delete
  events").
* A server can answer differently to different clients, regions or times; one report sees one answer.
* For MCP, a subset of the specification is checked. Use the official conformance suite for full coverage.
* OpenAPI checks focus on what tool generation relies on; use a full linter (e.g. Spectral) for style.
* Agent Card signatures are counted, not verified.
