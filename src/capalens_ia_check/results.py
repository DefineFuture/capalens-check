"""Collect one outcome per check, then emit them in catalogue order; a check never reached is ``unknown``."""

from __future__ import annotations

from typing import Any

from .checks import CHECKS, for_kind
from .model import Report, Result


class Results:
    def __init__(self, report: Report) -> None:
        self.report = report
        self._by_id: dict[str, Result] = {}

    def set(self, check_id: str, outcome: str, message: str, **evidence: Any) -> None:
        self._by_id[check_id] = Result(CHECKS[check_id], outcome, message, evidence)

    def has(self, check_id: str) -> bool:
        return check_id in self._by_id

    def outcome(self, check_id: str) -> str | None:
        result = self._by_id.get(check_id)
        return result.outcome if result else None

    def rest(self, outcome: str, message: str) -> None:
        """Every check of this kind not set yet gets ``outcome`` (used when nothing further can be observed)."""
        for check in for_kind(self.report.kind):
            if check.id not in self._by_id:
                self.set(check.id, outcome, message)

    def finish(self) -> Report:
        self.rest("unknown", "not reached")
        self.report.results = [self._by_id[c.id] for c in for_kind(self.report.kind)]
        return self.report.finish()
