# -*- coding: utf-8 -*-
"""全局工具注册表：按角色发工具。

说明：
- 真正生效的归属关系由 `@register(roles=[...])` 写入 REGISTRY（唯一事实来源）；
- 本文件的 TOOL_ROLES 只是**文档映射**，供 struct.md 与人工核对使用，
  tools_for() 不读它，避免两处配置打架。
"""

from config import AGENT_PERMISSION_MODE, TOOL_NET_POLICY
from lead_agent.core.toolkit.decorator import REGISTRY

# 业务角色（Supervisor 不持工具）
ALL_TOOL_ROLES = ("flow", "collect", "extract", "outreach")

# 工具 ↔ 角色矩阵（文档映射，新增工具时同步更新这里与 struct.md）
TOOL_ROLES = {
    "document.parse_document": ("flow", "collect", "extract", "outreach"),  # 全部角色
    "collect.gen_urls": ("collect", "flow"),
    "collect.crawl_pages": ("collect", "flow"),
    "collect.crawl_status": ("collect", "flow"),
    "extract.extract_leads": ("extract", "flow"),
    "extract.clean_leads": ("extract", "flow"),
    "extract.query_leads": ("extract", "outreach", "flow"),
    "verify.verify_emails": ("extract", "flow"),
    "outreach.draft_mail": ("outreach", "flow"),
    "outreach.send_mails": ("outreach", "flow"),
    "outreach.mail_stats": ("outreach", "flow"),
}

_LOADED = False


def load_tools() -> None:
    """导入所有工具模块，触发 @register 完成登记（幂等）。"""
    global _LOADED
    if _LOADED:
        return
    from lead_agent.tools import (  # noqa: F401  导入即注册
        collect,
        document,
        extract,
        outreach,
        verify,
    )

    _LOADED = True


class GlobalRegistry:
    """工具注册表的只读视图。"""

    def tools_for(self, role: str) -> dict[str, dict]:
        """返回某个角色可用的工具：name -> {func, description, roles}。"""
        load_tools()
        if not role:
            return {}
        result: dict[str, dict] = {}
        for name, item in REGISTRY.items():
            if "*" in item["roles"] or role in item["roles"]:
                result[name] = {
                    "func": item["func"],
                    "description": item["description"],
                    "roles": list(item["roles"]),
                }
        return result

    def get(self, name: str) -> dict | None:
        load_tools()
        return REGISTRY.get(name)

    def names(self) -> list[str]:
        load_tools()
        return sorted(REGISTRY)

    def describe(self, role: str) -> str:
        """生成给 LLM 看的工具清单文本（名称 + docstring 首行 + 参数）。"""
        lines = []
        for name, item in self.tools_for(role).items():
            sig = str(getattr(item["func"], "__annotations__", {}))
            lines.append(f"- {name}：{item['description']}")
        return "\n".join(lines) if lines else "（当前角色没有可用工具）"

    def policy(self) -> dict:
        return {
            "permission_mode": AGENT_PERMISSION_MODE,
            "net_policy": TOOL_NET_POLICY,
        }


GLOBAL_REGISTRY = GlobalRegistry()

__all__ = ["GLOBAL_REGISTRY", "TOOL_ROLES", "ALL_TOOL_ROLES", "load_tools"]
