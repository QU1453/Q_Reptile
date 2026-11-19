# -*- coding: utf-8 -*-
"""全流程智能体：采集 → 抽取 → 清洗 → 写信，一条龙。"""

from lead_agent.Agents.base import ReActAgentBase


class FlowAgent(ReActAgentBase):
    role = "flow"
    system_prompt = (
        "你是全流程智能体，按「采集→抽取→清洗→写信」顺序推进，"
        "每步只调用一个工具，拿到结果再进入下一步；数据缺失时如实说明，不要编造。"
    )

    def classic_flow_reply(self, text: str, sid: str):
        trace: list[dict] = []
        lines: list[str] = ["全流程（规则兜底模式）："]

        _, raw = self.use("extract.query_leads", {"limit": 3, "source": "raw"}, sid, trace)
        lines.append(f"1) 原始线索：{raw.get('total', 0)} 条")

        _, cleaned = self.use("extract.clean_leads", {}, sid, trace)
        lines.append(
            f"2) 清洗后：{cleaned.get('clean', 0)} 条，有效邮箱 {cleaned.get('valid', 0)} 个"
            f"（去重丢弃 {cleaned.get('dropped', 0)} 条）"
        )

        leads = cleaned.get("leads") or []
        if leads:
            lead = leads[0]
            _, mail = self.use(
                "outreach.draft_mail",
                {
                    "company": lead.get("company", ""),
                    "country": lead.get("country", ""),
                    "snippet": f"官网 {lead.get('website', '')}".strip(),
                },
                sid,
                trace,
            )
            lines.append(f"3) 开发信草稿（{mail.get('chars', 0)} 字符）：\n{mail.get('body', '')}")
        else:
            lines.append("3) 暂无可写信的线索：先把 HTML 放进 raw/ 或补充线索表。")

        _, mail_stats = self.use("outreach.mail_stats", {}, sid, trace)
        lines.append(
            f"4) 发送记录：已发 {mail_stats.get('sent', 0)} 封，"
            f"回复率 {mail_stats.get('reply_rate', 0)}"
        )
        return "\n".join(lines), trace


__all__ = ["FlowAgent"]
