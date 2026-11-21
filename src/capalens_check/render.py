"""Report formats: text (terminal), JSON (machine), Markdown (PR comments, Actions summaries), SARIF 2.1.0."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from . import __version__
from .checks import CHECKS
from .model import OUTCOMES, Report, now, totals

TAG = {"pass": "PASS", "fail": "FAIL", "review": "REVIEW", "unknown": "UNKNOWN", "skip": "SKIP"}
NOTE = "No score: 'review' is a candidate for a human, never a verdict. Read-only metadata requests only."
RUN_FORMAT = "capalens-check.run/1"


def summary_line(counts: dict[str, int]) -> str:
    return ", ".join(f"{counts[o]} {o}" for o in OUTCOMES)


def text(reports: list[Report], *, verbose: bool = False) -> str:
    lines: list[str] = []
    for rep in reports:
        title = f"{rep.name} - " if rep.name else ""
        lines.append(f"capalens-check {__version__} | {title}{rep.kind} {rep.target}")
        for r in rep.results:
            if r.outcome == "skip" and not verbose:
                continue
            lines.append(f"  [{TAG[r.outcome]:<7}] {r.check.id:<9} {r.check.title} - {r.message}")
            if verbose and r.evidence:
                lines.append("            " + json.dumps(r.evidence, ensure_ascii=False)[:400])
        tail = f" | {rep.requests} request(s)" if rep.kind == "mcp" else ""
        lines.append(f"  Summary: {summary_line(rep.counts())}{tail}")
        lines.extend(f"  Note: {n}" for n in rep.notes)
        lines.append("")
    if len(reports) > 1:
        lines.append(f"All targets: {summary_line(totals(reports))}")
    lines.append(NOTE)
    return "\n".join(lines) + "\n"


def as_json(reports: list[Report]) -> dict[str, Any]:
    if len(reports) == 1:
        return reports[0].to_json()
    return {
        "format": RUN_FORMAT,
        "tool": {"name": "capalens-check", "version": __version__},
        "generatedAt": now(),
        "summary": totals(reports),
        "reports": [r.to_json() for r in reports],
    }


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def markdown(reports: list[Report]) -> str:
    out: list[str] = ["# capalens-check report", ""]
    if len(reports) > 1:
        out += [
            "| Target | Kind | " + " | ".join(o for o in OUTCOMES) + " |",
            "| --- | --- |" + " --- |" * len(OUTCOMES),
        ]
        for rep in reports:
            c = rep.counts()
            out.append(
                f"| {_cell(rep.name or rep.target)} | {rep.kind} | " + " | ".join(str(c[o]) for o in OUTCOMES) + " |"
            )
        out.append("")
    for rep in reports:
        out += [f"## {_cell(rep.name or rep.kind)}: `{rep.target}`", "", f"**{summary_line(rep.counts())}**", ""]
        out += ["| Outcome | Check | Title | Detail |", "| --- | --- | --- | --- |"]
        for r in rep.results:
            link = f"[{r.check.id}]({r.check.reference})"
            out.append(f"| {TAG[r.outcome]} | {link} | {_cell(r.check.title)} | {_cell(r.message)} |")
        attention = [r for r in rep.results if r.outcome in ("fail", "review") and r.evidence]
        if attention:
            out += ["", "<details><summary>Evidence for fail and review</summary>", ""]
            for r in attention:
                out += [
                    f"**{r.check.id}**",
                    "",
                    "```json",
                    json.dumps(r.evidence, ensure_ascii=False, indent=2)[:4000],
                    "```",
                    "",
                ]
            out.append("</details>")
        out += [""] + [f"> {n}" for n in rep.notes] + ([""] if rep.notes else [])
    out.append(f"_{NOTE}_")
    return "\n".join(out) + "\n"


def _level(outcome: str, level: str) -> str:
    if outcome == "fail":
        return "error" if level == "must" else "warning"
    return "warning" if outcome == "review" else "note"


def sarif(reports: list[Report], *, include_unknown: bool = False) -> dict[str, Any]:
    """SARIF 2.1.0: one result per fail or review (and unknown when asked). Locations name the target."""
    used = sorted({r.check.id for rep in reports for r in rep.results})
    rules = []
    for cid in used:
        c = CHECKS[cid]
        rules.append(
            {
                "id": c.id,
                "name": c.title,
                "shortDescription": {"text": c.title},
                "fullDescription": {"text": c.rationale},
                "helpUri": c.reference,
                "defaultConfiguration": {"level": "error" if c.level == "must" else "warning"},
                "properties": {
                    "layer": c.layer,
                    "level": c.level,
                    "kind": c.kind,
                    "tags": ["capalens", c.kind, c.layer],
                },
            }
        )
    results = []
    wanted = ("fail", "review", "unknown") if include_unknown else ("fail", "review")
    for rep in reports:
        for r in rep.results:
            if r.outcome not in wanted:
                continue
            fingerprint = hashlib.sha256(f"{r.check.id}|{rep.kind}|{rep.target}".encode()).hexdigest()
            results.append(
                {
                    "ruleId": r.check.id,
                    "level": _level(r.outcome, r.check.level),
                    "message": {"text": f"[{r.outcome}] {r.message}"},
                    "locations": [{"physicalLocation": {"artifactLocation": {"uri": rep.target.replace("\\", "/")}}}],
                    "partialFingerprints": {"capalensCheck/v1": fingerprint},
                    "properties": {"outcome": r.outcome, "targetKind": rep.kind, "evidence": r.evidence},
                }
            )
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "capalens-check",
                        "version": __version__,
                        "informationUri": "https://github.com/Capalens/capalens-check",
                        "rules": rules,
                    }
                },
                "results": results,
                "invocations": [{"executionSuccessful": True, "endTimeUtc": now()}],
            }
        ],
    }


def render(reports: list[Report], fmt: str, *, verbose: bool = False) -> str:
    if fmt == "json":
        return json.dumps(as_json(reports), ensure_ascii=False, indent=2) + "\n"
    if fmt == "markdown":
        return markdown(reports)
    if fmt == "sarif":
        return json.dumps(sarif(reports), ensure_ascii=False, indent=2) + "\n"
    return text(reports, verbose=verbose)
