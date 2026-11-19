# -*- coding: utf-8 -*-
"""预算：限制单次会话的工具调用次数。"""

import threading

from config import MAX_TOOL_CALLS

_used: dict[str, int] = {}
_lock = threading.Lock()


def remaining(session_id: str) -> int:
    """返回该会话剩余可用次数。"""
    with _lock:
        return max(0, MAX_TOOL_CALLS - _used.get(session_id, 0))


def consume(session_id: str) -> tuple[bool, str]:
    """消耗一次预算；超限时返回 (False, 原因)。"""
    with _lock:
        used = _used.get(session_id, 0)
        if used >= MAX_TOOL_CALLS:
            return False, f"工具调用预算用尽（{MAX_TOOL_CALLS} 次/会话）"
        _used[session_id] = used + 1
        return True, f"已用 {used + 1}/{MAX_TOOL_CALLS}"


def reset(session_id: str) -> None:
    with _lock:
        _used.pop(session_id, None)


def snapshot() -> dict:
    with _lock:
        return {"limit": MAX_TOOL_CALLS, "sessions": dict(_used)}


__all__ = ["remaining", "consume", "reset", "snapshot"]
