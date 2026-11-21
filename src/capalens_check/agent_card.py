"""Static checks of an A2A Agent Card (file or URL). Signatures are recorded, not verified.

Two shapes are recognised: the 1.0 card (``supportedInterfaces``) and the earlier 0.x card (a top-level
``url``). proto3 JSON names in snake_case are read as camelCase. A URL without a path is read at
``/.well-known/agent-card.json``.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any

from .model import Report
from .net import HttpClient, is_loopback, load_json_bytes, public_location
from .results import Results
from .screens import text_screens
from .sources import is_url, read

WELL_KNOWN = "/.well-known/agent-card.json"
REQUIRED_V1 = (
    "name",
    "description",
    "supportedInterfaces",
    "version",
    "capabilities",
    "defaultInputModes",
    "defaultOutputModes",
    "skills",
)
REQUIRED_V0 = (
    "name",
    "description",
    "url",
    "version",
    "capabilities",
    "defaultInputModes",
    "defaultOutputModes",
    "skills",
)
INTERFACE_REQUIRED = ("url", "protocolBinding", "protocolVersion")
SKILL_REQUIRED = ("id", "name", "description", "tags")


def _camel(key: str) -> str:
    return re.sub(r"_([a-z0-9])", lambda m: m.group(1).upper(), key) if "_" in key else key


def _norm(obj: Any) -> Any:
    """camelCase member names of the card, its interfaces, capabilities and skills (not of maps such as
    securitySchemes, whose keys are names)."""
    if isinstance(obj, dict):
        return {_camel(k): v for k, v in obj.items()}
    return obj


def _present(card: dict[str, Any], key: str) -> bool:
    value = card.get(key)
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return isinstance(value, dict)


def card_url(location: str) -> str:
    parts = urllib.parse.urlsplit(location)
    if parts.path in ("", "/"):
        return urllib.parse.urlunsplit((parts.scheme, parts.netloc, WELL_KNOWN, "", ""))
    return location


def check(location: str, http: HttpClient | None = None, *, name: str | None = None) -> Report:
    source = card_url(location) if is_url(location) else location
    report = Report("agent-card", public_location(source) if is_url(source) else source, name)
    res = Results(report)
    data, problem = read(source, http)
    if http is not None:
        report.requests = http.requests
    if data is None:
        res.set("A2A-001", "unknown", problem or "unreadable")
        res.rest("unknown", "the card could not be read")
        return res.finish()
    try:
        raw = load_json_bytes(data)
    except (ValueError, UnicodeDecodeError) as exc:
        res.set("A2A-001", "fail", f"invalid JSON: {exc}")
        res.rest("unknown", "the card could not be parsed")
        return res.finish()
    if not isinstance(raw, dict):
        res.set("A2A-001", "fail", "the card is not a JSON object")
        res.rest("unknown", "the card is not an object")
        return res.finish()
    res.set("A2A-001", "pass", "parsed")
    card = _norm(raw)
    shape = "1.0" if "supportedInterfaces" in card or "url" not in card else "0.x"
    report.facts["cardShape"] = shape

    required = REQUIRED_V1 if shape == "1.0" else REQUIRED_V0
    missing = [k for k in required if not _present(card, k)]
    interfaces = [_norm(i) for i in card.get("supportedInterfaces") or [] if isinstance(i, dict)]
    if shape == "1.0":
        for idx, item in enumerate(interfaces):
            missing += [f"supportedInterfaces[{idx}].{k}" for k in INTERFACE_REQUIRED if not _present(item, k)]
    if missing:
        res.set("A2A-002", "fail", f"missing or empty: {', '.join(missing[:12])}", missing=missing, shape=shape)
    else:
        res.set("A2A-002", "pass", f"all required fields of a {shape} card present")

    skills = [_norm(s) for s in card.get("skills") or [] if isinstance(s, dict)]
    problems: list[str] = []
    for idx, skill in enumerate(skills):
        absent = [k for k in SKILL_REQUIRED if not _present(skill, k)]
        if absent:
            problems.append(f"skills[{idx}] ({skill.get('id', '?')}): {', '.join(absent)}")
        tags = skill.get("tags")
        if isinstance(tags, list) and not all(isinstance(t, str) for t in tags):
            problems.append(f"skills[{idx}]: tags must be strings")
    ids = [s.get("id") for s in skills if isinstance(s.get("id"), str)]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if not skills:
        res.set("A2A-003", "fail" if "skills" in required else "skip", "no skills listed")
    elif problems or dupes:
        res.set("A2A-003", "fail", f"{len(problems)} skill problem(s), {len(dupes)} duplicate id(s)",
                problems=problems[:20], duplicates=dupes)  # fmt: skip
    else:
        res.set("A2A-003", "pass", f"{len(skills)} skill(s)")

    urls = [i.get("url") for i in interfaces] if shape == "1.0" else [card.get("url")]
    if shape == "0.x":
        urls += [_norm(i).get("url") for i in card.get("additionalInterfaces") or [] if isinstance(i, dict)]
    urls = [u for u in urls if isinstance(u, str) and u]
    insecure = [u for u in urls if not u.lower().startswith("https://") and not is_loopback(u)]
    if not urls:
        res.set("A2A-004", "skip", "no interface URL")
    elif insecure:
        res.set(
            "A2A-004",
            "fail",
            f"{len(insecure)} interface URL(s) without HTTPS",
            urls=[public_location(u) for u in insecure],
        )
    else:
        res.set("A2A-004", "pass", f"{len(urls)} interface URL(s)")

    schemes = card.get("securitySchemes")
    names = set(schemes) if isinstance(schemes, dict) else set()
    referenced: set[str] = set()
    for req in card.get("securityRequirements") or []:  # 1.0: [{"schemes": {"name": {"list": [...]}}}]
        if isinstance(req, dict) and isinstance(req.get("schemes"), dict):
            referenced |= set(req["schemes"])
    for req in card.get("security") or []:  # 0.x: [{"name": [scopes]}]
        if isinstance(req, dict):
            referenced |= set(req)
    unknown = sorted(referenced - names)
    if not referenced:
        res.set("A2A-005", "skip", "no security requirements declared")
    elif unknown:
        res.set("A2A-005", "fail", f"undeclared scheme(s): {', '.join(unknown)}", undeclared=unknown)
    else:
        res.set("A2A-005", "pass", f"{len(referenced)} scheme reference(s) declared")

    units = [(k, card[k]) for k in ("name", "description") if isinstance(card.get(k), str)]
    for skill in skills:
        sid = skill.get("id", "?")
        units += [(f"skills[{sid}].{k}", skill[k]) for k in ("name", "description") if isinstance(skill.get(k), str)]
        examples = skill.get("examples")
        units += (
            [(f"skills[{sid}].examples", e) for e in examples if isinstance(e, str)]
            if isinstance(examples, list)
            else []
        )
    text_screens(res, units)
    report.facts.update(
        name=card.get("name") if isinstance(card.get("name"), str) else None,
        version=card.get("version") if isinstance(card.get("version"), str) else None,
        skillCount=len(skills),
        interfaces=[
            {
                "binding": i.get("protocolBinding"),
                "url": public_location(i["url"]) if isinstance(i.get("url"), str) else None,
            }
            for i in interfaces
        ],
        signatures=len(card.get("signatures") or []) if isinstance(card.get("signatures"), list) else 0,
    )
    if report.facts["signatures"]:
        report.notes.append("The card carries signatures; this tool does not verify them.")
    return res.finish()
