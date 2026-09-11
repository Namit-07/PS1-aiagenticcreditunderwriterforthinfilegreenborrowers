"""Tiny dependency-free YAML parser for the simple subset used in policy files.

Supports comments, ``key: value`` scalars (strings / ints / floats / booleans),
nested mappings via indentation, and dash-lists (``- item``). It is intentionally
limited — if PyYAML is installed we use it instead.
"""

from __future__ import annotations

from typing import Any


def _scalar(text: str) -> Any:
    text = text.strip().strip('"').strip("'")
    lower = text.lower()
    if lower in {"true", "yes", "on"}:
        return True
    if lower in {"false", "no", "off", "null", "none", "~"}:
        return False
    try:
        if "." in text or "e" in lower:
            return float(text)
        return int(text)
    except ValueError:
        return text


def parse(text: str) -> dict[str, Any]:
    """Parse YAML text into a dict (subset)."""
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        content = raw.strip()
        if content.startswith("#"):
            continue
        lines.append((indent, content))

    node, _ = _parse_block(lines, 0)
    return node if isinstance(node, dict) else {}


def _parse_block(lines: list[tuple[int, str]], start: int) -> tuple[Any, int]:
    root: Any = {}
    list_items: list[Any] = []
    in_list = False
    i = start
    base_indent = lines[start][0] if start < len(lines) else 0

    while i < len(lines):
        indent, content = lines[i]
        if indent < base_indent:
            break
        if indent > base_indent:
            # Nested block under the previous key
            child, i = _parse_block(lines, i)
            if in_list:
                list_items.append(child)
            else:
                root[_last_key(root)] = child
            continue

        if content.startswith("- "):
            item = content[2:].strip()
            if ":" in item:
                k, v = item.split(":", 1)
                child, _ = _parse_block(lines, i)  # not used
                list_items.append({k.strip(): _scalar(v)})
            else:
                list_items.append(_scalar(item))
            in_list = True
            i += 1
            # consume deeper items under this dash if any
            continue

        if in_list and ":" not in content:
            list_items.append(_scalar(content))
            i += 1
            continue

        in_list = False
        if ":" in content:
            key, _, value = content.partition(":")
            key = key.strip()
            val = value.strip()
            if val == "":
                # could open a nested map
                if i + 1 < len(lines) and lines[i + 1][0] > indent:
                    child, i = _parse_block(lines, i + 1)
                    root[key] = child
                    continue
                root[key] = {}
            else:
                root[key] = _scalar(val)
            i += 1
        else:
            i += 1

    if in_list and not root:
        return list_items, i
    return root, i


def _last_key(root: dict[str, Any]) -> str:
    return next(reversed(root)) if root else ""