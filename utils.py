from __future__ import annotations

from typing import Any


def cast_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return []


def cast_dict(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(key): str(item) for key, item in value.items() if item}
    return {}


def cast_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
