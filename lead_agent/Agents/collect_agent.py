# -*- coding: utf-8 -*-
"""采集智能体：生成 URL、批量抓取、查抓取状态。"""

import re

from lead_agent.Agents.base import ReActAgentBase

URL_RE = re.compile(r"https?://[^\s，,；;）)]+")


class CollectAgent(ReActAgentBase):
    role = "collect"
    system_prompt = (
        "你是采集智能体，只负责把公开名录页抓成本地 HTML 并记录日志，"
        "不做字段判断、不发邮件；不确定的源先问清楚域名与分页规则。"
    )

    def classic_collect_reply(self, text: str, sid: str):
        trace: list[dict] = []
        _, status = self.use("collect.crawl_status", {}, sid, trace)
        stat = status.get("by_status", {})
        lines = [
            "采集状态（规则兜底模式）：",
            f"- 日志总记录：{status.get('total', 0)} 条，成功 {stat.get('ok', 0)} 条，失败 {stat.get('failed', 0)} 条",
            f"- 最近失败：{len(status.get('recent_failed', []))} 条",
        ]

        urls = URL_RE.findall(text)
        if urls:
            base = urls[0].rstrip("/")
            ok, gen = self.use(
                "collect.gen_urls",
                {"base_url": base, "list_pattern": "", "start_page": 1, "end_page": 1},
                sid,
                trace,
            )
            if ok:
                lines.append(f"- 已根据输入生成 {gen.get('count', 0)} 条待抓 URL：{gen.get('urls', [])}")
                lines.append("- 真正抓取需显式调用 crawl_pages 并 confirm=true（会联网，请先确认源站条款）。")
        else:
            lines.append("- 如需生成分页 URL，请在问题里给出站点地址与分页规则（如 /list?page={page}）。")
        return "\n".join(lines), trace


__all__ = ["CollectAgent"]
