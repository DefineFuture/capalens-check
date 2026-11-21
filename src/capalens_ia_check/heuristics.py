"""Heuristics over tool and document text. Candidates for human review, never verdicts.

Shared with the CapaLens detection engine (``action-heuristic/3``, ``poisoning-lexicon/0.1``):

* action labels: ``declared`` (MCP annotations) and ``heuristic`` (a lexicon over the tool's own text);
* annotation conflicts: a tool declared read-only (or not destructive) whose text says otherwise — a
  candidate for review, never an observation of a write or an execution. Negation, field roles and the
  object and target of add-type words are taken into account; every hit carries its counting basis;
* poisoning candidates: lexicon and structural signals (hidden Unicode, exfiltration URLs, local secret
  paths), with the triggering fragment.

Nothing here is a security assessment. "No candidate" means "nothing found by these word lists".
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import cache
from importlib import resources
from typing import Any

LEXICON_VERSION = "poisoning-lexicon/0.1"


@cache
def lexicon() -> dict[str, Any]:
    with resources.files("capalens_ia_check").joinpath("data/poisoning_lexicon.json").open("rb") as fh:
        data: dict[str, Any] = json.load(fh)
    return data


def _compile(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


ACTION_METHOD = "action-heuristic/3"
_MAX_EVIDENCE = 16

# Words per label (whole words; a few inflections where the noun reading is rare). "updates", "posts",
# "copies", "runs" and "moves" are left out: as nouns ("list workflow runs") they are common. "uploads"
# is kept although it can be a noun: missing an upload in a read-only tool costs more than a candidate.
_ACTION_WORDS = {
    "read": _compile(
        [
            r"\b(get|gets|list|lists|read|reads|fetch|fetches|search|query|lookup|look up|find|describe|show|view|"
            r"retrieve|retrieves|count)\b"
        ]
    ),
    "write": _compile(
        [
            r"\b(create|creates|add|adds|insert|inserts|update|edit|modify|modifies|set|put|patch|write|writes|"
            r"upload|uploads|rename|renames|move|copy|send|sends|post|publish|publishes|delete|deletes|remove|removes|drop|"
            r"purge|purges|reset|resets|truncate|truncates|destroy|destroys|revoke|revokes|disable|disables|"
            r"overwrite|overwrites)\b"
        ]
    ),
    "execute": _compile(
        [
            r"\b(run|exec|execute|executes|invoke|invokes|spawn|spawns|shell|command|script|eval|compile|deploy|"
            r"deploys|restart|restarts|kill|kills|terminate|terminates)\b"
        ]
    ),
    "orchestrate": _compile(
        [
            r"\b(schedule|schedules|cron|workflow|pipeline|orchestrat\w*|trigger|triggers|automate|automates|"
            r"batch job|agent)\b"
        ]
    ),
}
# Whole words: v1 matched prefixes, so "dropdown" read as destructive.
_DESTRUCTIVE = re.compile(
    r"\b(delete|deletes|deleted|remove|removes|removed|drop|drops|dropped|purge|purges|purged|reset|resets|truncate|"
    r"truncates|truncated|destroy|destroys|destroyed|wipe|wipes|wiped|overwrite|overwrites|permanent|permanently)\b",
    re.IGNORECASE,
)
_HIDDEN_UNICODE = re.compile("[​-‏ -‮⁠-⁤﻿­]")  # as in v1

# Negation (v2): a word is negated when a negation cue precedes it in the same sentence, nothing between
# them turns the sentence ("but", "then", ...), and the sentence has no exception ("unless", "except", ...)
# after the cue — "does not delete files unless force is true" still counts.
# Sentences (v3) end at . ; ! ? followed by a space, the end or a capital, or at a line break, so a version
# such as "pricing-0.4.2" or a path such as "metadata.sidecarSha256" stays inside its sentence.
_SENTENCE_BREAK = re.compile(r"[.;!?](?=\s|$|[A-Z])|\n")
# A cue joined by a hyphen is part of a word, not a negation (v3): "Return not-collected ..., or deletes ...".
_NEGATION = re.compile(
    r"(?<!-)\b(does not|do not|did not|doesn't|don't|didn't|will not|won't|never|cannot|can't|can not|no longer|"
    r"not|without)\b(?!-)",
    re.IGNORECASE,
)
_RESET = re.compile(r"\b(but|then|however|instead|yet|although|while|whereas)\b", re.IGNORECASE)
_EXCEPTION = re.compile(r"\b(unless|except|other than|only if|only when)\b", re.IGNORECASE)
# After an auxiliary ("does not", "cannot") the negated verbs are base forms, so a third-person form right
# after "and" or a comma starts a new predicate: "does not delete anything and wipes the cache" counts "wipes".
_AUXILIARY = re.compile(
    r"(does not|do not|did not|doesn't|don't|didn't|will not|won't|cannot|can't|can not)", re.IGNORECASE
)
_NEW_PREDICATE = re.compile(r"(,|\band)\s*$", re.IGNORECASE)
_IDENTIFIER_SPLIT = re.compile(r"[_\-.\s]+|(?<=[a-z0-9])(?=[A-Z])")

# Objects and targets (v3). "Add" is the one write verb whose usual reading in a read-only tool is "put
# something into the answer" ("includeChecklist:true adds review steps", "adds them to comparison-summary").
# So an add-type word is judged by the head noun of what it adds and of where it goes:
# * a target or object that is a thing a write lands on (database, record, customer, file, ...) counts;
# * a target that is part of the answer (response, summary, ...) does not count;
# * an object that is part of the answer does not count when a parameter is the subject
#   ("pricing:\"summary\" adds ... status"), i.e. the sentence says what a call option puts in the answer;
# * anything else is unclear and, in the tool's own text, stays a candidate for the reviewers.
# In a parameter description, any write word counts when its object or target is such a thing ("If true,
# adds the item to the customer's cart"); other write words there still do not count. A name is a short noun
# compound ("post_index"), so it is not read this way: there only strong and read words count, as in v2.
# Nouns are compared in the singular; the lists are short on purpose: a noun missing from both is unclear.
_ADD_VERBS = frozenset({"add", "adds", "insert", "inserts"})


def _words(text: str) -> frozenset[str]:
    return frozenset(text.split())


_EXTERNAL_NOUNS = _words(
    "account bucket branch calendar cart catalog channel charge cluster comment commit config configuration contact "
    "customer database db directory disk email event file folder group index invoice issue key member message order "
    "payment permission project queue record repo repository role secret server setting storage store subscription "
    "table team ticket token user webhook wiki workspace"
)
_OUTPUT_NOUNS = _words(
    "answer breakdown caveat checklist citation column comparison context count date detail dimension example "
    "excerpt explanation field guidance guide hint link metadata note output overview preview reply report "
    "requirement response result section snippet status step summary total view warning"
)
_TARGET_PREPOSITIONS = frozenset({"to", "into", "onto", "in"})
_PHRASE_STOP = _words(
    "about after as at because before but by except for from if of on only per since so than that then though "
    "unless until via when whenever where whether which while who with within without"
)
_DETERMINERS = _words("a an all any each every her his its my our some that the their these this those your")
_TOKEN = re.compile(r"[A-Za-z0-9][\w'./-]*|[^\w\s]")
_ASSIGNMENT = re.compile(r"\b[A-Za-z_][\w.]*\s*[:=]\s*(?:true|false|null|\"|\[|\{|-?\d)")
_IDENTIFIER_LIKE = re.compile(r"[A-Z_0-9]")  # camelCase, snake_case or digits: not an ordinary English word


def _negated(sentence: str, at: int, word: str) -> bool:
    for cue in _NEGATION.finditer(sentence[:at]):
        if _RESET.search(sentence[cue.end() : at]):
            continue
        if (
            _AUXILIARY.fullmatch(cue.group(0))
            and word.lower().endswith("s")
            and _NEW_PREDICATE.search(sentence[cue.end() : at])
        ):
            continue
        return not _EXCEPTION.search(sentence[cue.start() :])
    return False


def _fields(tool: dict[str, Any]) -> list[tuple[str, str, str]]:
    """(field, role, text): the name split into words, title, description, then input-field descriptions."""
    out = []
    name = tool.get("name")
    if isinstance(name, str) and name:
        out.append(("name", "tool-name", " ".join(w for w in _IDENTIFIER_SPLIT.split(name) if w)))
    for key in ("title", "description"):
        if isinstance(tool.get(key), str) and tool[key]:
            out.append((key, "tool-text", tool[key]))
    schema = tool.get("inputSchema")
    props = schema.get("properties") if isinstance(schema, dict) else None
    for prop, sub in props.items() if isinstance(props, dict) else ():
        if isinstance(sub, dict) and isinstance(sub.get("description"), str):
            out.append((f"inputSchema/properties/{prop}/description", "parameter-text", sub["description"]))
    return out


def _sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_BREAK.split(text) if s.strip()]


def _head(token: str) -> str:
    """The head noun of a token, lower case and singular when the singular is a listed noun."""
    parts = [p for p in re.split(r"[-/.]", token.lower()) if p]
    word = re.sub(r"'s?$", "", parts[-1]) if parts else ""
    candidates = [word]
    if word.endswith("ies"):
        candidates.append(word[:-3] + "y")
    if word.endswith("es"):
        candidates.append(word[:-2])
    if word.endswith("s"):
        candidates.append(word[:-1])
    return next((c for c in candidates if c in _EXTERNAL_NOUNS or c in _OUTPUT_NOUNS), word)


def _heads(tokens: list[str]) -> list[str]:
    """Head nouns of a phrase: the last word of each part joined by "and" / "or"."""
    heads: list[str] = []
    current: list[str] = []
    for tok in tokens:
        if tok.lower() in ("and", "or"):
            heads += [_head(current[-1])] if current else []
            current = []
        elif tok.lower() not in _DETERMINERS:
            current.append(tok)
    return heads + ([_head(current[-1])] if current else [])


def _phrase(tokens: list[str], start: int) -> list[str]:
    """Words from ``start`` up to punctuation, a stop word, a target preposition or a verb form in -ing."""
    out: list[str] = []
    for tok in tokens[start:]:
        low = tok.lower()
        if tok in ('"', "'"):
            continue
        if not tok[0].isalnum() or low in _PHRASE_STOP or low in _TARGET_PREPOSITIONS:
            break
        if out and low.endswith("ing") and len(low) > 4:
            break
        out.append(tok)
        if len(out) >= 8:
            break
    return out


def _target(body: str, m: re.Match[str], props: set[str]) -> tuple[str, list[str], bool]:
    """(external | output-target | output-object | unclear, deciding words, a parameter is the subject)."""
    tokens = [t.rstrip(".'/-") or t for t in _TOKEN.findall(body[m.end() :])]
    obj = _heads(_phrase(tokens, 0))
    dest: list[str] = []
    for i, tok in enumerate(tokens):  # the first target preposition in the same clause
        low = tok.lower()
        if not tok[0].isalnum() and tok not in ('"', "'"):
            break
        if low in ("which", "who", "that", "when", "if", "unless", "but", "then", "while", "because"):
            break
        if low in _TARGET_PREPOSITIONS:
            dest = _heads(_phrase(tokens, i + 1))
            break
    before = body[: m.start()]
    # a property of this tool named before the verb (identifier-like only: "task" or "at" are ordinary words);
    # ordered by position, so the evidence does not depend on set order
    mentions = []
    for p in props:
        found = re.search(rf"(?<![\w.]){re.escape(p)}(?!\w)", before) if _IDENTIFIER_LIKE.search(p) else None
        if found:
            mentions.append((found.start(), p))
    named = [p for _, p in sorted(mentions)]
    assignment = _ASSIGNMENT.search(before)
    by_parameter = bool(assignment or named)
    if any(h in _EXTERNAL_NOUNS for h in dest):
        return "external", [h for h in dest if h in _EXTERNAL_NOUNS], by_parameter
    if any(h in _OUTPUT_NOUNS for h in dest):
        return "output-target", [h for h in dest if h in _OUTPUT_NOUNS], by_parameter
    if any(h in _EXTERNAL_NOUNS for h in obj):
        return "external", [h for h in obj if h in _EXTERNAL_NOUNS], by_parameter
    if any(h in _OUTPUT_NOUNS for h in obj):
        subject = [assignment.group(0).split(":")[0].split("=")[0].strip()] if assignment else named[:1]
        return "output-object", subject + [h for h in obj if h in _OUTPUT_NOUNS], by_parameter
    return "unclear", obj + dest, by_parameter


def _judge(
    label: str, word: str, role: str, body: str, m: re.Match[str], props: set[str]
) -> tuple[bool, str, list[str]]:
    """(counted, basis, deciding words) for one hit that is not negated."""
    if label in ("destructive", "execute"):
        return True, "strong-word", []
    if label == "read":
        return True, "read-word", []
    add = word.lower() in _ADD_VERBS
    if label == "write" and ((add and role == "tool-text") or role == "parameter-text"):
        kind, terms, by_parameter = _target(body, m, props)
        if kind == "external":
            return True, "write-to-external-object", terms
        if role == "tool-text":
            if kind == "output-target":
                return False, "add-to-output", terms
            if kind == "output-object" and by_parameter:
                return False, "add-output-set-by-parameter", terms
            return True, "add-target-unclear", terms
    if role == "tool-text":
        return True, "tool-text-word", []
    # A parameter's description says what the parameter controls (often what goes into the answer); a name
    # is a short label. Weak words there count only with an external object or target (above).
    return False, "weak-word-outside-tool-text", []


def _matches(tool: dict[str, Any]) -> list[dict[str, Any]]:
    """Every lexicon hit with its field, role, negation, whether it counts and why (see ``action_labels``)."""
    schema = tool.get("inputSchema")
    raw_props = schema.get("properties") if isinstance(schema, dict) else None
    props = {str(p) for p in raw_props} if isinstance(raw_props, dict) else set()
    hits = []
    for field, role, text in _fields(tool):
        for body in _sentences(text):
            found: list[tuple[str, re.Match[str]]] = [
                (label, m) for label, pats in _ACTION_WORDS.items() for pat in pats for m in pat.finditer(body)
            ]
            found += [("destructive", m) for m in _DESTRUCTIVE.finditer(body)]
            for label, m in found:
                negated = _negated(body, m.start(), m.group(0))
                terms: list[str] = []
                if negated:
                    counted, basis = False, "negated"
                else:
                    counted, basis, terms = _judge(label, m.group(0), role, body, m, props)
                hits.append(
                    {
                        "field": field,
                        "role": role,
                        "label": label,
                        "word": m.group(0),
                        "negated": negated,
                        "counted": counted,
                        "basis": basis,
                        "basisTerms": terms,
                        "fragment": body.strip()[:160],
                    }
                )
    return hits


def action_hits(tool: dict[str, Any]) -> list[dict[str, Any]]:
    """Every hit of one tool, unbounded and in text order (``action_labels`` keeps at most 16)."""
    return _matches(tool)


def _text_of(tool: dict[str, Any]) -> str:
    parts = [str(tool.get("name", "")), str(tool.get("title", "")), str(tool.get("description", ""))]
    schema = tool.get("inputSchema")
    if isinstance(schema, dict):
        props = schema.get("properties")
        for prop in props.values() if isinstance(props, dict) else ():
            if isinstance(prop, dict) and isinstance(prop.get("description"), str):
                parts.append(prop["description"])
    return "\n".join(parts)


def action_labels(tool: dict[str, Any]) -> dict[str, Any]:
    """Declared vs. text-suggested actions of one tool (``action-heuristic/3``).

    A hit counts when it is not negated and is a strong word (destructive or execute) anywhere, a read
    word, a write word with an external object or target anywhere, or another word in the title or
    description — except an add-type word whose target, or (with a parameter as subject) whose object, is
    part of the answer. A conflict candidate is a counted write or execute word next to
    ``readOnlyHint: true``, or a counted destructive word next to ``destructiveHint: false``. ``evidence``
    lists every hit, counted or not, with its ``basis``, so a reviewer sees why.
    """
    raw_ann = tool.get("annotations")
    ann: dict[str, Any] = raw_ann if isinstance(raw_ann, dict) else {}
    declared: list[str] = []
    if ann.get("readOnlyHint") is True:
        declared.append("read")
    if ann.get("destructiveHint") is True:
        declared.append("write")
    if ann.get("readOnlyHint") is False and "write" not in declared:
        declared.append("write")
    hits = _matches(tool)
    counted = [h for h in hits if h["counted"]]
    labels = {("write" if h["label"] == "destructive" else h["label"]) for h in counted}
    heuristic = sorted(labels) or ["unknown"]
    reasons = []
    if ann.get("readOnlyHint") is True and any(h["label"] in ("write", "execute", "destructive") for h in counted):
        reasons.append("read-only-declared-but-text-writes-or-executes")
    destructive_text = any(h["label"] == "destructive" for h in counted)
    if ann.get("destructiveHint") is False and destructive_text:
        reasons.append("not-destructive-declared-but-text-destroys")
    evidence = sorted(hits, key=lambda h: (not h["counted"], h["field"], h["word"].lower()))[:_MAX_EVIDENCE]
    return {
        "name": tool.get("name"),
        "declared": declared or ["unknown"],
        "heuristic": heuristic,
        "annotationConflict": bool(reasons),
        "conflictReasons": reasons,
        "destructiveLanguage": destructive_text,
        "method": ACTION_METHOD,
        "evidence": evidence,
        "evidenceCount": len(hits),
    }


def poisoning_candidates(tool: dict[str, Any]) -> list[dict[str, Any]]:
    return candidates_in_text(_text_of(tool))


def candidates_in_text(text: str) -> list[dict[str, Any]]:
    """Lexicon hits in one piece of text (a tool, a card, a skill): candidates, never verdicts."""
    lex = lexicon()
    hits: list[dict[str, Any]] = []
    for category, patterns in lex["categories"].items():
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                start = max(0, m.start() - 40)
                hits.append({"category": category, "pattern": pattern, "fragment": text[start : m.end() + 40][:200]})
                break
    hidden = _HIDDEN_UNICODE.findall(text)
    if hidden:
        hits.append(
            {
                "category": "hidden-unicode",
                "pattern": "invisible-characters",
                "fragment": ",".join(sorted({unicodedata.name(c, hex(ord(c))) for c in hidden})),
            }
        )
    mixed = [c for c in text if unicodedata.category(c) == "Lo" and ord(c) > 0x2FF] and re.search(r"[A-Za-z]", text)
    if mixed and lex.get("flagMixedScripts", False):
        hits.append({"category": "mixed-scripts", "pattern": "script-mixing", "fragment": text[:120]})
    return hits


def analyse_texts(units: list[tuple[str, str]], subject: str) -> dict[str, Any]:
    """Poisoning candidates over labelled texts of a card or skill (ADR-0019), same lexicon as tools.

    ``units`` are ``(label, text)`` pairs, e.g. ``("skills/0/description", "...")``. The label names where
    the text came from; it is never searched itself.
    """
    candidates = [{"unit": label, "hits": h} for label, text in units if (h := candidates_in_text(text))]
    return {
        "lexiconVersion": LEXICON_VERSION,
        "subject": subject,
        "textCount": len(units),
        "textUnits": [label for label, _ in units],
        "poisoningCandidates": candidates,
        "poisoningCandidateCount": len(candidates),
        "verdict": "candidates-only",
    }


def analyse_tools(tools: list[dict[str, Any]]) -> dict[str, Any]:
    labels = [action_labels(t) for t in tools]
    candidates = [{"tool": t.get("name"), "hits": h} for t in tools if (h := poisoning_candidates(t))]
    all_labels = sorted(
        {label for item in labels for label in item["heuristic"] + item["declared"] if label != "unknown"}
    )
    return {
        "lexiconVersion": LEXICON_VERSION,
        "actionMethod": ACTION_METHOD,
        "toolCount": len(tools),
        "actionLabels": labels,
        "serverActionLabels": all_labels,
        "annotationConflicts": sum(1 for item in labels if item["annotationConflict"]),
        "annotationConflictTools": [item["name"] for item in labels if item["annotationConflict"]],
        "poisoningCandidates": candidates,
        "poisoningCandidateCount": len(candidates),
        "verdict": "candidates-only",
    }
