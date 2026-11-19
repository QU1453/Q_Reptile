# -*- coding: utf-8 -*-
"""记忆访问权限门：L0 / L1 / L2 三级简化实现。

- L0：公开信息（如公开官网、名录），任何模式可读；
- L1：项目内数据（线索表、抓取日志），readonly 及以上可读；
- L2：写操作 / 外发邮件，plan 模式需显式确认，readonly 一律拒绝。
"""

from config import AGENT_PERMISSION_MODE

LEVELS = {
    "L0": "公开信息读取",
    "L1": "项目内数据读取",
    "L2": "写操作与外发触达",
}


def check(level: str, project_id: str | None = None) -> tuple[bool, str]:
    """返回 (是否放行, 原因)。project_id 用于将来多项目隔离，当前只做校验占位。"""
    level = (level or "L0").upper()
    mode = AGENT_PERMISSION_MODE

    if level not in LEVELS:
        return False, f"未知权限等级：{level}"
    if mode == "readonly":
        if level == "L0":
            return True, "readonly：允许公开读取"
        return False, f"readonly：禁止 {level}（{LEVELS[level]}）"
    if mode == "plan" and level == "L2":
        # 由约束层继续要求 confirm=true，这里只标记为「需确认」
        return True, "plan：L2 需调用方 confirm=true"

    if project_id is not None and not str(project_id).strip():
        return False, "project_id 为空"

    return True, f"{mode}：允许 {level}（{LEVELS[level]}）"


__all__ = ["LEVELS", "check"]
