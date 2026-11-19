# -*- coding: utf-8 -*-
"""约束层入口：四道检查（权限 / 路径 / 网络 / 危险写操作）。

任何工具调用都必须先过这里，顺序固定：
1. 权限门（L1 读 / L2 写）
2. 路径检查（不得逃出 TOOL_PATH_ROOTS）
3. 网络策略（外网工具是否放行）
4. 危险写操作（plan 模式需 confirm=true）
"""

from urllib.parse import urlparse

from config import AGENT_PERMISSION_MODE, TOOL_NET_ALLOWLIST, TOOL_NET_POLICY
from lead_agent.core.constraint import budget, validator
from lead_agent.core.constraint.rules import DANGEROUS_WRITE, NET_TOOLS, WRITE_TOOLS
from lead_agent.memory.access import check as access_check


def _truthy(value) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def _check_network(args: dict) -> tuple[bool, str]:
    if TOOL_NET_POLICY == "block":
        return False, "网络策略为 block，禁止一切外网请求"

    urls = args.get("urls") or []
    if isinstance(urls, str):
        urls = [u.strip() for u in urls.splitlines() if u.strip()]
    for url in urls:
        parsed = urlparse(str(url))
        if parsed.scheme not in ("http", "https"):
            return False, f"仅允许 http/https：{url}"
        if TOOL_NET_ALLOWLIST:
            host = (parsed.hostname or "").lower()
            if host not in TOOL_NET_ALLOWLIST:
                return False, f"域名不在白名单：{host}"
    return True, ""


def check_tool_call(name: str, args: dict | None = None) -> tuple[bool, str]:
    """返回 (是否放行, 说明)。"""
    args = args or {}

    # 第 1 道：权限
    level = "L2" if name in WRITE_TOOLS else "L1"
    ok, reason = access_check(level, project_id="default")
    if not ok:
        return False, f"权限拒绝：{reason}"

    # 第 2 道：路径
    ok, reason = validator.check_paths(args)
    if not ok:
        return False, f"路径拒绝：{reason}"

    # 第 3 道：网络
    if name in NET_TOOLS:
        ok, reason = _check_network(args)
        if not ok:
            return False, f"网络拒绝：{reason}"

    # 第 4 道：危险写操作
    if AGENT_PERMISSION_MODE == "plan" and name in DANGEROUS_WRITE:
        if not _truthy(args.get("confirm", False)):
            return False, f"{name} 属于危险写操作，plan 模式需 confirm=true"

    return True, "通过四道检查"


def check_budget(session_id: str) -> tuple[bool, str]:
    """工具调用预算检查（由 Agent 在执行前调用）。"""
    return budget.consume(session_id)


__all__ = ["check_tool_call", "check_budget"]
