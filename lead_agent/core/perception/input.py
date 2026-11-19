# -*- coding: utf-8 -*-
"""输入清洗：去首尾空白、压缩空行、超长截断。"""

import re

_SPACE_RE = re.compile(r"[ \t\u3000]+")
_BLANK_RE = re.compile(r"\n{3,}")


def clean_input(text: str, max_chars: int = 4000) -> str:
    """清洗用户输入；超长时截断并加省略标记。"""
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    raw = _SPACE_RE.sub(" ", raw)
    raw = _BLANK_RE.sub("\n\n", raw).strip()
    if len(raw) > max_chars:
        return raw[:max_chars].rstrip() + "\n…（输入过长已截断）"
    return raw


__all__ = ["clean_input"]
