# -*- coding: utf-8 -*-
"""记忆总装配：把短期窗口与长期条目组合成一次问答可用的记忆摘要。"""

from config import PATHS
from lead_agent.memory import long_term, short_term
from lead_agent.memory.access import check


class MemoryManager:
    """remember 写入，recall 取出；权限门在写入前统一检查。"""

    def remember(self, session_id: str, user_text: str, answer: str, agent: str = "") -> dict:
        ok, reason = check("L1", project_id=session_id)
        if not ok:
            return {"saved": False, "reason": reason}

        short_term.append(session_id, "user", user_text)
        short_term.append(session_id, "assistant", answer)
        long_term.add(
            text=f"[{agent or 'agent'}] 问：{user_text[:120]} ｜ 答：{answer[:200]}",
            tags=[agent] if agent else [],
            session_id=session_id,
        )
        return {"saved": True, "reason": reason, "file": str(PATHS["short_term"].name)}

    def recall(self, session_id: str, query: str = "", n: int = 4) -> str:
        """返回可直接塞进提示词的记忆摘要文本。"""
        ok, _ = check("L0")
        if not ok:
            return ""

        parts: list[str] = []
        history = short_term.recent(session_id, n)
        if history:
            lines = [f"{item.get('role')}: {item.get('content', '')[:120]}" for item in history]
            parts.append("最近对话：\n" + "\n".join(lines))

        entries = long_term.search(query, n) if query else long_term.all_entries(n)
        if entries:
            lines = [f"- {item.get('text', '')[:160]}" for item in entries]
            parts.append("相关长期记忆：\n" + "\n".join(lines))

        return "\n\n".join(parts)

    def reset(self, session_id: str) -> int:
        return short_term.clear(session_id)


MEMORY = MemoryManager()

__all__ = ["MemoryManager", "MEMORY"]
