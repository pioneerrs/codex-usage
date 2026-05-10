from __future__ import annotations

import re
from typing import Dict


MARKER_RE = re.compile(
    r"<!--\s*codex-usage:(user|assistant|tool|file-context)\s*-->",
    re.IGNORECASE,
)


EMPTY_PARTS = {
    "userText": "",
    "assistantText": "",
    "toolText": "",
    "fileContextText": "",
}


def parse_transcript(text: str, kind: str = "mixed") -> Dict[str, str]:
    parts = dict(EMPTY_PARTS)
    normalized_kind = kind.replace("_", "-")

    if normalized_kind != "mixed":
        key = _kind_to_key(normalized_kind)
        parts[key] = text
        return parts

    matches = list(MARKER_RE.finditer(text))
    if not matches:
        parts["assistantText"] = text
        return parts

    if matches[0].start() > 0:
        parts["assistantText"] += text[: matches[0].start()].strip()

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        key = _kind_to_key(match.group(1).lower())
        segment = text[start:end].strip()
        if segment:
            if parts[key]:
                parts[key] += "\n\n"
            parts[key] += segment

    return parts


def _kind_to_key(kind: str) -> str:
    return {
        "user": "userText",
        "assistant": "assistantText",
        "tool": "toolText",
        "file-context": "fileContextText",
    }[kind]

