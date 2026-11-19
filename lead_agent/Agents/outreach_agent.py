# -*- coding: utf-8 -*-
"""触达智能体：写开发信、限速发送、看回复统计。"""

from lead_agent.Agents.base import ReActAgentBase


class OutreachAgent(ReActAgentBase):
    role = "outreach"
    system_prompt = (
        "你是触达智能体，负责按线索写四段式开发信、按每日上限发送并统计回复；"
        "invalid 邮箱绝不发送，每封信必须带退订说明，不做无人值守群发。"
    )

    def classic_outreach_reply(self, text: str, sid: str):
        trace: list[dict] = []
        lines = ["触达（规则兜底模式）："]

        ok, leads = self.use(
            "extract.query_leads", {"limit": 3, "source": "clean", "status": "valid"}, sid, trace
        )
        rows = (leads.get("leads") or []) if ok else []
        lines.append(f"- 可触达线索：{leads.get('total', 0) if ok else 0} 条（只取 valid 邮箱）")

        for lead in rows[:2]:
            ok, mail = self.use(
                "outreach.draft_mail",
                {
                    "company": lead.get("company", ""),
                    "country": lead.get("country", ""),
                    "snippet": f"官网 {lead.get('website', '')}".strip(),
                },
                sid,
                trace,
            )
            if ok:
                lines.append(f"\n【样例开发信 · {mail.get('company') or '未命名公司'}】")
                lines.append(f"主题：{mail.get('subject')}")
                lines.append(mail.get("body", ""))

        _, stats = self.use("outreach.mail_stats", {}, sid, trace)
        lines.append(
            f"\n- 发送统计：已发 {stats.get('sent', 0)} 封，回复 {stats.get('replied', 0)} 封，"
            f"回复率 {stats.get('reply_rate', 0)}，每日上限 {stats.get('daily_limit', 0)}"
        )
        lines.append("- 实际发送（模拟）需调用 send_mails 并 confirm=true。")
        return "\n".join(lines), trace


__all__ = ["OutreachAgent"]
