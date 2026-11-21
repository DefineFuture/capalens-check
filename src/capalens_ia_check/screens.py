"""SEC-001 and SEC-002 over labelled texts of any target kind."""

from __future__ import annotations

from typing import Any

from .heuristics import candidates_in_text
from .results import Results


def text_screens(res: Results, units: list[tuple[str, str]]) -> None:
    """SEC-001 (wording) and SEC-002 (invisible characters) over labelled texts."""
    wording: list[dict[str, Any]] = []
    hidden: list[dict[str, Any]] = []
    for label, text in units:
        for hit in candidates_in_text(text):
            entry = {"where": label, "category": hit["category"], "fragment": hit["fragment"]}
            (hidden if hit["category"] == "hidden-unicode" else wording).append(entry)
    if wording:
        res.set("SEC-001", "review", f"{len(wording)} candidate(s) for review", candidates=wording[:20])
    else:
        res.set("SEC-001", "pass", f"no candidate in {len(units)} text(s)", textsScanned=len(units))
    if hidden:
        res.set("SEC-002", "review", f"invisible characters in {len(hidden)} text(s)", candidates=hidden[:20])
    else:
        res.set("SEC-002", "pass", f"none in {len(units)} text(s)", textsScanned=len(units))
