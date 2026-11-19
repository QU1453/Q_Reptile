# -*- coding: utf-8 -*-
"""上下文组装：系统提示 + 死规则 + 记忆摘要 + 用户输入，按字符预算分配。"""

from config import CONTEXT_CHAR_BUDGET


def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 20)].rstrip() + "\n…（已截断）"


def build_context(
    system_prompt: str,
    rules: str,
    memory_text: str,
    user_text: str,
    budget: int | None = None,
) -> str:
    """四段式上下文；总长度不超过 budget，优先保证用户输入完整。"""
    total = int(budget or CONTEXT_CHAR_BUDGET)
    user_part = _clip(user_text, int(total * 0.35))
    system_part = _clip(system_prompt, int(total * 0.25))
    rules_part = _clip(rules, int(total * 0.15))
    memory_part = _clip(memory_text, int(total * 0.25))

    blocks = [
        "【系统提示】\n" + (system_part or "（无）"),
        "【死规则】\n" + (rules_part or "（无）"),
        "【记忆摘要】\n" + (memory_part or "（无）"),
        "【用户输入】\n" + user_part,
    ]
    return "\n\n".join(blocks)


__all__ = ["build_context"]
