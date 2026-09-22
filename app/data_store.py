import json
from typing import Any

from .config import SCHEDULES_FILE


def load_schedules() -> list[dict[str, Any]]:
    if not SCHEDULES_FILE.exists():
        return []
    with open(SCHEDULES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_schedules(schedules: list[dict[str, Any]]) -> None:
    SCHEDULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEDULES_FILE, "w", encoding="utf-8") as f:
        json.dump(schedules, f, ensure_ascii=False, indent=2)


def upsert_teacher(schedules: list[dict[str, Any]], teacher: dict[str, Any]) -> list[dict[str, Any]]:
    """Replace the existing entry for this teacher name (if any) and append the new one."""
    name = teacher.get("name")
    result = [t for t in schedules if t.get("name") != name]
    result.append(teacher)
    return result
