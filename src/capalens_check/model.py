"""Checks, results and reports. A result is evidence about one target at one time, never a score.

Outcomes:

* ``pass``    the property was observed;
* ``fail``    the opposite was observed (a MUST or SHOULD of the specification, or a stated property);
* ``review``  a heuristic found a candidate for a human to look at — never a verdict;
* ``unknown`` it could not be determined (no answer, authentication required, budget spent);
* ``skip``    the check does not apply to this target.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

from . import __version__

OUTCOMES = ("pass", "fail", "review", "unknown", "skip")
REPORT_FORMAT = "capalens-check.report/1"


@dataclass(frozen=True)
class Check:
    id: str
    title: str
    kind: str  # mcp | openapi | agent-card | skill | any
    layer: str  # L0 reachability and transport, L1 protocol and format, L3 security candidates
    level: str  # must | should | heuristic | info
    reference: str
    rationale: str

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "kind": self.kind,
            "layer": self.layer,
            "level": self.level,
            "reference": self.reference,
            "rationale": self.rationale,
        }


@dataclass
class Result:
    check: Check
    outcome: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.outcome not in OUTCOMES:
            raise ValueError(f"unknown outcome {self.outcome!r}")

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.check.id,
            "title": self.check.title,
            "layer": self.check.layer,
            "level": self.check.level,
            "outcome": self.outcome,
            "message": self.message,
            "evidence": self.evidence,
            "reference": self.check.reference,
        }


def obj(value: Any) -> dict[str, Any]:
    """A member that should be an object; from a target, anything else reads as absent."""
    return value if isinstance(value, dict) else {}


def arr(value: Any) -> list[Any]:
    """A member that should be an array; from a target, anything else reads as absent."""
    return value if isinstance(value, list) else []


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Report:
    kind: str
    target: str  # a URL without credentials or query values, or a path as given
    name: str | None = None
    results: list[Result] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
    requests: int = 0
    started_at: str = field(default_factory=now)
    finished_at: str | None = None
    notes: list[str] = field(default_factory=list)

    def add(self, result: Result) -> None:
        self.results.append(result)

    def counts(self) -> dict[str, int]:
        out = dict.fromkeys(OUTCOMES, 0)
        for r in self.results:
            out[r.outcome] += 1
        return out

    def finish(self) -> Report:
        self.finished_at = now()
        return self

    def to_json(self) -> dict[str, Any]:
        return {
            "format": REPORT_FORMAT,
            "tool": {"name": "capalens-check", "version": __version__},
            "target": {"kind": self.kind, "location": self.target, "name": self.name},
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "requests": self.requests,
            "summary": self.counts(),
            "results": [r.to_json() for r in self.results],
            "facts": self.facts,
            "notes": self.notes,
            "disclaimer": (
                "Evidence about one target at one time. No score; 'review' is a candidate for a human, "
                "never a verdict; nothing was called beyond read-only metadata requests."
            ),
        }


def totals(reports: list[Report]) -> dict[str, int]:
    total = dict.fromkeys(OUTCOMES, 0)
    for rep in reports:
        for key, value in rep.counts().items():
            total[key] += value
    return total
