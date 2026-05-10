from __future__ import annotations

from typing import Optional

from .errors import UsageError


def count_tokens(text: str, model: Optional[str] = None, encoding_name: str = "o200k_base") -> int:
    if not text:
        return 0

    try:
        import tiktoken
    except ModuleNotFoundError:
        raise UsageError(
            "Token estimation requires `tiktoken`, but it is not installed. "
            "Install it with `python3 -m pip install -r requirements.txt` or "
            "`python3 -m pip install -e .`, then retry."
        )

    encoding = None
    if model and model != "unknown":
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = None
    if encoding is None:
        try:
            encoding = tiktoken.get_encoding(encoding_name)
        except Exception as exc:
            raise UsageError(
                f'Tokenizer encoding "{encoding_name}" is unavailable. '
                "Check `.codex-usage/config.json` or reinstall `tiktoken`."
            ) from exc
    return len(encoding.encode(text))

