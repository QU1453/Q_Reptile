# -*- coding: utf-8 -*-
"""短期记忆：按会话窗口追加 jsonl，读取最近 N 条。"""

import json
import time
from pathlib import Path

from config import PATHS


def _path() -> Path:
    path = PATHS["short_term"]
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def append(session_id: str, role: str, content: str) -> dict:
    """追加一条会话消息。"""
    record = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "session_id": session_id or "",
        "role": role,
        "content": str(content)[:2000],
    }
    with open(_path(), "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def recent(session_id: str, n: int = 6) -> list[dict]:
    """读取某个会话最近 n 条消息（旧 → 新）。"""
    path = _path()
    if not path.exists():
        return []
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("session_id") == session_id:
                rows.append(rec)
    return rows[-max(1, int(n)):]


def clear(session_id: str) -> int:
    """清空某个会话的短期记忆，返回删除条数。"""
    path = _path()
    if not path.exists():
        return 0
    kept: list[str] = []
    removed = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("session_id") == session_id:
                removed += 1
            else:
                kept.append(line if line.endswith("\n") else line + "\n")
    path.write_text("".join(kept), encoding="utf-8")
    return removed


__all__ = ["append", "recent", "clear"]
