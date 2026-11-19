# -*- coding: utf-8 -*-
"""主控智能体：规则路由，不调用 LLM、不持有工具。"""

import re

from lead_agent.core.perception.input import clean_input

# 按顺序匹配，先命中者生效；全不中默认 collect
ROUTE_RULES = (
    ("flow", re.compile(r"全流程|一条龙|端到端|走一遍|从采集到")),
    ("collect", re.compile(r"采集|爬|抓取|URL|链接|名录")),
    ("extract", re.compile(r"抽取|清洗|去重|验证|邮箱|线索")),
    ("outreach", re.compile(r"开发信|写信|邮件|发送|回复率")),
)
DEFAULT_ROLE = "collect"


class Supervisor:
    """规则路由：把问题分给对应的业务智能体。"""

    role = "supervisor"

    def _route(self, text: str) -> str:
        for role, pattern in ROUTE_RULES:
            if pattern.search(text):
                return role
        return DEFAULT_ROLE

    def _agent(self, role: str):
        # 延迟导入，避免 Agents 包在初始化时互相引用
        from lead_agent.Agents.collect_agent import CollectAgent
        from lead_agent.Agents.extract_agent import ExtractAgent
        from lead_agent.Agents.flow_agent import FlowAgent
        from lead_agent.Agents.outreach_agent import OutreachAgent
        from lead_agent.Agents.summarizer import SummarizerAgent

        return {
            "flow": FlowAgent,
            "collect": CollectAgent,
            "extract": ExtractAgent,
            "outreach": OutreachAgent,
            "summarizer": SummarizerAgent,
        }.get(role, CollectAgent)()

    def ask(self, text: str, session_id: str | None = None) -> dict:
        role = self._route(clean_input(text))
        result = self._agent(role).ask(text, session_id)
        # 把路由结果附在 trace 首位，方便前端解释「为什么是这个智能体」
        result.setdefault("trace", [])
        result["trace"].insert(0, {"round": 0, "action": "route", "args": {}, "ok": True, "result": role})
        return result

    def stats(self) -> dict:
        """聚合看板数据（供 /api/stats 使用）。"""
        from lead_agent.core.constraint import budget
        from lead_agent.tools.catalog import lead_counts
        from lead_agent.tools.collect import crawl_status
        from lead_agent.tools.outreach import mail_stats
        from config import AGENT_PERMISSION_MODE, LLM_MODEL, TOOL_NET_POLICY

        return {
            "leads": lead_counts(),
            "crawl": crawl_status(),
            "mail": mail_stats(),
            "budget": budget.snapshot(),
            "model": LLM_MODEL or "未配置（走规则兜底）",
            "permission_mode": AGENT_PERMISSION_MODE,
            "net_policy": TOOL_NET_POLICY,
        }


__all__ = ["Supervisor", "ROUTE_RULES", "DEFAULT_ROLE"]
