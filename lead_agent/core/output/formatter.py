# -*- coding: utf-8 -*-
"""输出格式化：统一为 {answer, trace, agent}。"""

import json


def _safe(item):
    try:
        json.dumps(item, ensure_ascii=False)
        return item
    except TypeError:
        return str(item)


def build(answer: str, trace: list | None = None, agent: str = "") -> dict:
    """统一返回值；trace 里的不可序列化对象转成字符串。"""
    return {
        "answer": str(answer or "").strip(),
        "trace": [_safe(item) for item in (trace or [])],
        "agent": agent or "",
    }


def error(message: str, agent: str = "") -> dict:
    """出错时的统一结构。"""
    return build(f"处理失败：{message}", [], agent)


__all__ = ["build", "error"]
