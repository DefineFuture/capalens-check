"""Strict reader for the YAML front matter of a ``SKILL.md``. No YAML library (shared with the CapaLens engine).

The reference parser uses ``strictyaml`` (no tags, no flow style, no implicit typing: every scalar is a
string). This reader accepts the subset a skill's front matter needs and nothing more:

* the file starts with a line ``---`` and the front matter ends at the next line ``---``;
* top-level ``key: value`` lines; a value is a plain scalar, a single- or double-quoted scalar, or a
  block scalar (``|``, ``>``, with ``-``/``+`` chomping) whose lines are indented;
* ``key:`` with nothing after it, followed by indented ``key: value`` lines, is a one-level mapping
  (for ``metadata``); its values are scalars;
* blank lines and ``#`` comment lines are ignored.

Anything else is reported, never guessed: flow style (``[``, ``{``), tags (``!``), anchors and aliases
(``&``, ``*``), sequences (``- ``), directives (``%``), deeper nesting, tabs in indentation and
multi-line plain scalars are ``unsupported``; a missing closing ``---``, a line without ``:``, a duplicate
key, an unterminated quote or inconsistent indentation is ``invalid``. Keys are never interpreted.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MARKER = "---"
Value = str | dict[str, str]


@dataclass
class FrontMatter:
    status: str  # ok | invalid | unsupported
    fields: dict[str, Value] = field(default_factory=dict)
    body: str = ""
    end_offset: int = 0  # byte offset where the front matter block ends (after the closing marker line)
    problems: list[str] = field(default_factory=list)


class _Problem(Exception):
    def __init__(self, status: str, message: str) -> None:
        super().__init__(message)
        self.status = status


def _unsupported(message: str) -> _Problem:
    return _Problem("unsupported", message)


def _invalid(message: str) -> _Problem:
    return _Problem("invalid", message)


def _unquote(text: str, line_no: int) -> str:
    quote = text[0]
    escapes = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "/": "/", "r": "\r", " ": " "}
    out: list[str] = []
    i = 1
    closed = False
    while i < len(text):
        ch = text[i]
        if ch == quote:
            if quote == "'" and text[i + 1 : i + 2] == "'":  # '' is an escaped single quote
                out.append("'")
                i += 2
                continue
            closed = True
            i += 1
            break
        if ch == "\\" and quote == '"':
            i += 1
            if i >= len(text) or text[i] not in escapes:
                raise _unsupported(f"line {line_no}: escape sequence not supported")
            out.append(escapes[text[i]])
        else:
            out.append(ch)
        i += 1
    rest = text[i:].strip()
    if not closed or (rest and not rest.startswith("#")):
        raise _invalid(f"line {line_no}: unterminated quoted scalar")
    return "".join(out)


def _scalar(text: str, line_no: int) -> str:
    """A plain or quoted scalar on one line. Everything is a string; nothing is typed."""
    text = text.strip()
    if not text:
        return ""
    if text[0] in "\"'":
        return _unquote(text, line_no)
    if text[0] in "[{!&*%@`|>":
        raise _unsupported(f"line {line_no}: value starts with {text[0]!r}")
    if text.startswith("- ") or text == "-":
        raise _unsupported(f"line {line_no}: sequence")
    if text.startswith("? "):
        raise _unsupported(f"line {line_no}: complex key")
    if " #" in text:
        text = text.split(" #", 1)[0].rstrip()
    return text


def _indent(line: str, line_no: int) -> int:
    stripped = line.lstrip(" ")
    if stripped.startswith("\t"):
        raise _unsupported(f"line {line_no}: tab indentation")
    return len(line) - len(stripped)


def _split_key(line: str, line_no: int) -> tuple[str, str]:
    key, sep, rest = line.partition(":")
    if not sep or not key.strip():
        raise _invalid(f"line {line_no}: no 'key:' on this line")
    if rest and not rest.startswith(" ") and rest.strip():
        raise _invalid(f"line {line_no}: no space after ':'")
    key = key.strip()
    if key[0] in "\"'[{!&*%-?":
        raise _unsupported(f"line {line_no}: key starts with {key[0]!r}")
    return key, rest.strip()


def _block_scalar(indicator: str, lines: list[str], start: int, line_no: int) -> tuple[str, int]:
    """Lines of a ``|`` / ``>`` block scalar from ``start``; returns (value, next index)."""
    style, chomp = indicator[0], indicator[1:]
    if chomp not in ("", "-", "+"):
        raise _unsupported(f"line {line_no}: block scalar indicator {indicator!r}")
    collected: list[str] = []
    i = start
    indent: int | None = None
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            collected.append("")
            i += 1
            continue
        width = _indent(line, i + 1)
        if indent is None:
            if width == 0:
                break
            indent = width
        if width < indent:
            break
        collected.append(line[indent:])
        i += 1
    if indent is None:
        raise _invalid(f"line {line_no}: block scalar without content")
    while collected and collected[-1] == "":
        collected.pop()
    if style == "|":
        text = "\n".join(collected)
    else:  # folded: single newlines become spaces, blank lines stay newlines
        parts: list[str] = []
        for item in collected:
            if item == "":
                parts.append("\n")
            elif parts and parts[-1] != "\n":
                parts.append(" " + item)
            else:
                parts.append(item)
        text = "".join(parts)
    if chomp == "+":
        text += "\n"
    elif chomp == "":
        text += "\n" if text else ""
    return text, i


def _parse_lines(lines: list[str]) -> dict[str, Value]:
    fields: dict[str, Value] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        line_no = i + 1
        if line.strip() == "" or line.lstrip().startswith("#"):
            i += 1
            continue
        if _indent(line, line_no) != 0:
            raise _invalid(f"line {line_no}: unexpected indentation")
        if line.startswith("- ") or line == "-":
            raise _unsupported(f"line {line_no}: sequence")
        key, rest = _split_key(line, line_no)
        if key in fields:
            raise _invalid(f"line {line_no}: duplicate key {key!r}")
        i += 1
        if rest and rest[0] in "|>":
            value, i = _block_scalar(rest, lines, i, line_no)
            fields[key] = value
            continue
        if rest:
            fields[key] = _scalar(rest, line_no)
            # a continuation line under a plain scalar is a multi-line plain scalar
            if i < len(lines) and lines[i].strip() and _indent(lines[i], i + 1) > 0:
                raise _unsupported(f"line {i + 1}: multi-line plain scalar")
            continue
        nested: dict[str, str] = {}
        indent: int | None = None
        while i < len(lines):
            sub = lines[i]
            if sub.strip() == "" or sub.lstrip().startswith("#"):
                i += 1
                continue
            width = _indent(sub, i + 1)
            if width == 0:
                break
            if indent is None:
                indent = width
            if width != indent:
                raise _invalid(f"line {i + 1}: inconsistent indentation")
            if sub.strip().startswith("- "):
                raise _unsupported(f"line {i + 1}: sequence")
            sub_key, sub_rest = _split_key(sub.strip(), i + 1)
            if sub_key in nested:
                raise _invalid(f"line {i + 1}: duplicate key {sub_key!r}")
            if not sub_rest:
                raise _unsupported(f"line {i + 1}: nesting deeper than one level")
            if sub_rest[0] in "|>":
                raise _unsupported(f"line {i + 1}: block scalar inside a mapping")
            nested[sub_key] = _scalar(sub_rest, i + 1)
            i += 1
        if indent is None:
            fields[key] = ""  # `key:` with nothing under it is an empty scalar
        else:
            fields[key] = nested
    return fields


def parse(data: bytes) -> FrontMatter:
    """Read the front matter of a SKILL.md. Never raises on content; the status says what happened."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return FrontMatter("invalid", problems=["not UTF-8"])
    if text.startswith("﻿"):
        text = text[1:]
    lines = text.split("\n")
    if not lines or lines[0].rstrip("\r") != MARKER:
        return FrontMatter("invalid", problems=["does not start with '---'"])
    end = None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r") == MARKER:
            end = i
            break
    if end is None:
        return FrontMatter("invalid", problems=["front matter not closed with '---'"])
    block = [line.rstrip("\r") for line in lines[1:end]]
    body = "\n".join(lines[end + 1 :])
    end_offset = len("\n".join(lines[: end + 1]).encode("utf-8"))
    for line in block:
        if line.startswith("%") or line == "...":
            return FrontMatter("unsupported", body=body, end_offset=end_offset, problems=["directive or document end"])
    try:
        fields = _parse_lines(block)
    except _Problem as exc:
        return FrontMatter(exc.status, body=body, end_offset=end_offset, problems=[str(exc)])
    return FrontMatter("ok", fields, body, end_offset)
