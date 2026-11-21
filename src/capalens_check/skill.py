"""Static checks of an Agent Skill: a directory with ``SKILL.md``. No file of the skill is executed."""

from __future__ import annotations

import os
import unicodedata
from pathlib import Path

from .frontmatter import parse
from .model import Report
from .results import Results
from .screens import text_screens

SKILL_FILES = ("SKILL.md", "skill.md")
ALLOWED_FIELDS = ("name", "description", "license", "compatibility", "metadata", "allowed-tools")
LIMITS = {"name": 64, "description": 1024, "compatibility": 500}
RECOMMENDED_BODY_LINES = 500
MAX_FILES = 2000
EXECUTABLE_SUFFIXES = (
    ".py", ".sh", ".bash", ".zsh", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl", ".php", ".ps1", ".bat", ".cmd",
    ".exe", ".jar",
)  # fmt: skip


def name_format_ok(name: str) -> bool:
    n = unicodedata.normalize("NFKC", name.strip())
    if not n or n.startswith("-") or n.endswith("-") or "--" in n:
        return False
    return all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in n)


def check(location: str, *, name: str | None = None) -> Report:
    path = Path(location)
    directory = path.parent if path.is_file() else path
    report = Report("skill", location, name)
    res = Results(report)
    skill_md = next((directory / f for f in SKILL_FILES if (directory / f).is_file()), None)
    if skill_md is None:
        res.set("SKILL-001", "fail", f"no SKILL.md in {directory}")
        res.rest("unknown", "no SKILL.md")
        return res.finish()
    fm = parse(skill_md.read_bytes())
    if fm.status != "ok":
        res.set("SKILL-001", "fail", f"front matter {fm.status}: {'; '.join(fm.problems)}")
        res.rest("unknown", "the front matter could not be read")
        return res.finish()
    res.set("SKILL-001", "pass", f"{skill_md.name}: front matter read")
    fields = fm.fields

    problems = [f"{k}: missing" for k in ("name", "description") if k not in fields]
    for key, limit in LIMITS.items():
        value = fields.get(key)
        if key not in fields:
            continue
        if not isinstance(value, str):
            problems.append(f"{key}: not a string")
        elif not value.strip():
            problems.append(f"{key}: empty")
        elif len(value) > limit:
            problems.append(f"{key}: {len(value)} characters (max {limit})")
    if problems:
        res.set("SKILL-002", "fail", "; ".join(problems), problems=problems)
    else:
        res.set("SKILL-002", "pass", "name and description present and within limits")

    skill_name = fields.get("name")
    if not isinstance(skill_name, str) or not skill_name.strip():
        res.set("SKILL-003", "skip", "no name to check")
    elif not name_format_ok(skill_name):
        res.set("SKILL-003", "fail", f"name {skill_name!r}: use lower-case letters, digits and single hyphens")
    elif unicodedata.normalize("NFKC", skill_name.strip()) != unicodedata.normalize("NFKC", directory.resolve().name):
        res.set("SKILL-003", "fail", f"name {skill_name!r} differs from the directory {directory.resolve().name!r}")
    else:
        res.set("SKILL-003", "pass", f"{skill_name!r} matches its directory")

    extra = sorted(set(fields) - set(ALLOWED_FIELDS))
    if extra:
        res.set("SKILL-004", "fail", f"unspecified field(s): {', '.join(extra)}", fields=extra)
    else:
        res.set("SKILL-004", "pass", f"{len(fields)} field(s), all specified")

    lines = fm.body.count("\n") + (1 if fm.body and not fm.body.endswith("\n") else 0)
    if lines > RECOMMENDED_BODY_LINES:
        res.set("SKILL-005", "fail", f"{lines} body lines (recommended under {RECOMMENDED_BODY_LINES})")
    else:
        res.set("SKILL-005", "pass", f"{lines} body line(s)")

    files: list[str] = []
    for root, dirs, names in os.walk(directory, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not (Path(root) / d).is_symlink())
        files += [str((Path(root) / n).relative_to(directory)).replace(os.sep, "/") for n in sorted(names)]
        if len(files) > MAX_FILES:
            report.notes.append(f"more than {MAX_FILES} files; listing stopped")
            break
    executables = sorted(f for f in files if f.lower().endswith(EXECUTABLE_SUFFIXES))
    res.set(
        "SKILL-006",
        "pass",
        f"{len(executables)} executable file(s) listed for review (never run)"
        if executables
        else "no executable files",
        executables=executables[:50],
    )
    description = fields.get("description")
    units: list[tuple[str, str]] = [("description", description)] if isinstance(description, str) else []
    units.append(("body", fm.body))
    text_screens(res, units)
    report.facts.update(
        name=skill_name if isinstance(skill_name, str) else None,
        fields=sorted(fields),
        fileCount=len(files),
        bodyLines=lines,
        allowedTools=fields.get("allowed-tools") if isinstance(fields.get("allowed-tools"), str) else None,
    )
    return res.finish()
