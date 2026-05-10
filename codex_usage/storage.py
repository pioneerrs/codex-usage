from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .errors import UsageError


DEFAULT_DIR = ".codex-usage"

DEFAULT_CONFIG = {
    "version": 1,
    "defaultEncoding": "o200k_base",
    "defaultLanguage": "auto",
    "defaultModel": "unknown",
    "defaultMode": "unknown",
    "multipliers": {
        "simple_chat": 1.5,
        "small_code_change": 2.5,
        "medium_code_task": 4,
        "large_repo_task": 6,
        "long_running_agent": 8,
        "unknown": 3,
    },
}


JSONL_FILES = ("groups.jsonl", "snapshots.jsonl", "turns.jsonl")


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def storage_dir_from(value: Optional[str]) -> Path:
    return Path(value or os.environ.get("CODEX_USAGE_DIR") or DEFAULT_DIR)


def init_storage(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    for filename in JSONL_FILES:
        path = data_dir / filename
        if not path.exists():
            path.touch()
    config_path = data_dir / "config.json"
    if not config_path.exists():
        write_json(config_path, DEFAULT_CONFIG)


def ensure_initialized(data_dir: Path) -> None:
    missing = [name for name in JSONL_FILES if not (data_dir / name).exists()]
    if missing or not (data_dir / "config.json").exists():
        raise UsageError(
            "Codex usage storage was not initialized. "
            "Run `codex-usage init` in this directory first."
        )


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_config(data_dir: Path) -> Dict[str, Any]:
    ensure_initialized(data_dir)
    path = data_dir / "config.json"
    try:
        with path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
    except json.JSONDecodeError as exc:
        raise UsageError(f"`{path}` contains invalid JSON at line {exc.lineno}. Fix it and retry.")
    merged = dict(DEFAULT_CONFIG)
    merged.update(config)
    merged["multipliers"] = dict(DEFAULT_CONFIG["multipliers"], **config.get("multipliers", {}))
    return merged


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise UsageError(
                    f"`{path}` has a damaged JSONL line at {line_number}: {exc.msg}. "
                    "Edit or remove that line, then retry."
                )
            if not isinstance(value, dict):
                raise UsageError(
                    f"`{path}` line {line_number} is not a JSON object. "
                    "Each JSONL line must be one object."
                )
            records.append(value)
    return records


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def load_groups(data_dir: Path) -> List[Dict[str, Any]]:
    ensure_initialized(data_dir)
    return read_jsonl(data_dir / "groups.jsonl")


def load_snapshots(data_dir: Path) -> List[Dict[str, Any]]:
    ensure_initialized(data_dir)
    return read_jsonl(data_dir / "snapshots.jsonl")


def load_turns(data_dir: Path) -> List[Dict[str, Any]]:
    ensure_initialized(data_dir)
    return read_jsonl(data_dir / "turns.jsonl")


def append_group(data_dir: Path, record: Dict[str, Any]) -> None:
    ensure_initialized(data_dir)
    append_jsonl(data_dir / "groups.jsonl", record)


def append_snapshot(data_dir: Path, record: Dict[str, Any]) -> None:
    ensure_initialized(data_dir)
    append_jsonl(data_dir / "snapshots.jsonl", record)


def append_turn(data_dir: Path, record: Dict[str, Any]) -> None:
    ensure_initialized(data_dir)
    append_jsonl(data_dir / "turns.jsonl", record)


def find_group(groups: Iterable[Dict[str, Any]], value: str) -> Dict[str, Any]:
    by_id = [group for group in groups if group.get("id") == value]
    if by_id:
        return by_id[0]

    by_name = [group for group in groups if group.get("name") == value]
    if len(by_name) == 1:
        return by_name[0]
    if len(by_name) > 1:
        raise UsageError(
            f'Task group name "{value}" is ambiguous. Use the task group id instead.'
        )
    raise UsageError(
        f'Task group "{value}" was not found. '
        "Run `codex-usage group list` to see available groups."
    )
