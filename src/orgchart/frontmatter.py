"""Minimal, strict front matter parser.

Why not PyYAML: the repo should be usable by anyone who clones it with a bare
Python, and the front matter only ever needs scalars, null and flow lists.
A strict subset is also a feature: contributors cannot sneak in anchors,
multi-line strings or nested maps that downstream tools then mis-handle.

Supported:
    key: value
    key: null
    key: [a, b, c]          (flow list of scalars; quotes optional)
    key: "quoted: value"    (double quotes when the value contains ':' or ',')
"""

from __future__ import annotations

import re

FENCE = "---"
_KEY = re.compile(r"^([a-z_][a-z0-9_]*):\s*(.*)$")


class FrontMatterError(ValueError):
    pass


def split(text: str) -> tuple[str, str]:
    """Return (front_matter_block, body). Raises when the fence is missing."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != FENCE:
        raise FrontMatterError("file must start with a '---' fence")
    for i in range(1, len(lines)):
        if lines[i].strip() == FENCE:
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1 :]).lstrip("\n")
    raise FrontMatterError("closing '---' fence not found")


def _scalar(raw: str):
    raw = raw.strip()
    if raw == "" or raw == "null" or raw == "~":
        return None
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    if raw in ("true", "false"):
        return raw == "true"
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    return raw


def _flow_list(raw: str) -> list:
    inner = raw.strip()[1:-1].strip()
    if not inner:
        return []
    items, buf, quote = [], "", None
    for ch in inner:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf += ch
        elif ch == ",":
            items.append(_scalar(buf))
            buf = ""
        else:
            buf += ch
    if buf.strip() or items:
        items.append(_scalar(buf))
    return items


def parse(text: str) -> tuple[dict, str]:
    """Parse a file's text into (front_matter_dict, body)."""
    block, body = split(text)
    data: dict = {}
    for n, line in enumerate(block.splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t":
            raise FrontMatterError(f"line {n}: indented lines (nested maps, block lists) are not allowed")
        m = _KEY.match(line)
        if not m:
            raise FrontMatterError(f"line {n}: expected 'key: value', got {line!r}")
        key, raw = m.group(1), m.group(2).strip()
        if key in data:
            raise FrontMatterError(f"line {n}: duplicate key {key!r}")
        if raw.startswith("["):
            if not raw.endswith("]"):
                raise FrontMatterError(f"line {n}: flow list for {key!r} must close on the same line")
            data[key] = _flow_list(raw)
        else:
            data[key] = _scalar(raw)
    return data, body


def dump(data: dict) -> str:
    """Serialise a flat dict back to a front matter block (used by exporters)."""
    out = [FENCE]
    for k, v in data.items():
        if v is None:
            out.append(f"{k}: null")
        elif isinstance(v, bool):
            out.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, list):
            out.append(f"{k}: [{', '.join(_quote(x) for x in v)}]")
        else:
            out.append(f"{k}: {_quote(v)}")
    out.append(FENCE)
    return "\n".join(out) + "\n"


def _quote(v) -> str:
    s = str(v)
    if any(c in s for c in ":,[]#\"'") or s != s.strip():
        return '"' + s.replace('"', '\\"') + '"'
    return s
