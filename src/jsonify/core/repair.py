"""Best-effort repair for common, safely recoverable JSON mistakes.

Every pass below is string-aware (it re-scans character by character and
only ever rewrites text *outside* of string literals), so none of the
transformations can accidentally corrupt a string value that happens to
contain a comma, a colon, or a quote character.

Handled cases:
    - Single-quoted strings -> double-quoted strings.
    - Trailing commas before ``}`` or ``]``.
    - Unquoted (bare-identifier) object keys.
    - Missing closing ``}``/``]`` at the end of the document (truncated JSON).

Anything outside these safely-recoverable cases (e.g. more closing
brackets than opening ones, or genuinely ambiguous syntax) is left alone.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

_BARE_KEY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?=\s*:)")


@dataclass(slots=True)
class RepairResult:
    """Outcome of attempting to repair a malformed JSON document."""

    text: str
    applied_fixes: list[str] = field(default_factory=list)
    is_valid: bool = False


def attempt_repair(text: str) -> RepairResult:
    """Try to fix common, safely recoverable JSON syntax mistakes."""

    fixes: list[str] = []
    working = text

    working, changed = _convert_single_quoted_strings(working)
    if changed:
        fixes.append("Converted single-quoted strings to double-quoted strings.")

    working, changed = _quote_bare_keys(working)
    if changed:
        fixes.append("Added missing quotes around object keys.")

    working, changed = _close_unbalanced_brackets(working)
    if changed:
        fixes.append("Closed unterminated objects/arrays.")

    # Runs last: closing brackets above can expose a trailing comma that
    # was previously at the very end of the text (not yet followed by a
    # '}'/']'), so trailing-comma cleanup has to happen after that.
    working, changed = _remove_trailing_commas(working)
    if changed:
        fixes.append("Removed trailing commas before '}' or ']'.")

    is_valid = _is_valid_json(working)

    return RepairResult(text=working, applied_fixes=fixes, is_valid=is_valid)


def _is_valid_json(text: str) -> bool:
    try:
        json.loads(text)
    except json.JSONDecodeError:
        return False
    return True


def _convert_single_quoted_strings(text: str) -> tuple[str, bool]:
    out: list[str] = []
    changed = False
    i = 0
    n = len(text)

    while i < n:
        char = text[i]

        if char == '"':
            start = i
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" and i + 1 < n else 1
            i += 1
            out.append(text[start:i])
            continue

        if char == "'":
            i += 1
            buffer: list[str] = ['"']
            while i < n and text[i] != "'":
                if text[i] == "\\" and i + 1 < n:
                    buffer.append(text[i : i + 2])
                    i += 2
                    continue
                if text[i] == '"':
                    buffer.append('\\"')
                    i += 1
                    continue
                buffer.append(text[i])
                i += 1
            i += 1
            buffer.append('"')
            out.append("".join(buffer))
            changed = True
            continue

        out.append(char)
        i += 1

    return "".join(out), changed


def _remove_trailing_commas(text: str) -> tuple[str, bool]:
    out: list[str] = []
    changed = False
    i = 0
    n = len(text)

    while i < n:
        char = text[i]

        if char == '"':
            start = i
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" and i + 1 < n else 1
            i += 1
            out.append(text[start:i])
            continue

        if char == ",":
            lookahead = i + 1
            while lookahead < n and text[lookahead] in " \t\r\n":
                lookahead += 1

            if lookahead < n and text[lookahead] in "}]":
                changed = True
                i += 1
                continue

        out.append(char)
        i += 1

    return "".join(out), changed


def _quote_bare_keys(text: str) -> tuple[str, bool]:
    out: list[str] = []
    changed = False
    i = 0
    n = len(text)

    while i < n:
        char = text[i]

        if char == '"':
            start = i
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" and i + 1 < n else 1
            i += 1
            out.append(text[start:i])
            continue

        match = _BARE_KEY_PATTERN.match(text, i)
        if match and (not out or out[-1] in "{, \t\r\n"):
            out.append(f'"{match.group(0)}"')
            changed = True
            i = match.end()
            continue

        out.append(char)
        i += 1

    return "".join(out), changed


def _close_unbalanced_brackets(text: str) -> tuple[str, bool]:
    stack: list[str] = []
    i = 0
    n = len(text)

    while i < n:
        char = text[i]

        if char == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" and i + 1 < n else 1
            i += 1
            continue

        if char in "{[":
            stack.append("}" if char == "{" else "]")
        elif char in "}]" and stack and stack[-1] == char:
            stack.pop()

        i += 1

    if not stack:
        return text, False

    return text + "".join(reversed(stack)), True
