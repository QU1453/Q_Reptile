# -*- coding: utf-8 -*-
"""总结智能体：汇总批次结果，不持有工具。"""

from lead_agent.Agents.base import ReActAgentBase
from lead_agent.tools.catalog import lead_counts
from lead_agent.tools.collect import crawl_status
from lead_agent.tools.outreach import mail_stats


class SummarizerAgent(ReActAgentBase):
    role = "summarizer"
    system_prompt = "你是总结智能体，只根据已有数据做汇总与复盘，不调用工具、不编造数字。"

    def classic_summarizer_reply(self, text: str, sid: str):
        counts = lead_counts()
        crawl = crawl_status()
        mails = mail_stats()

        lines = [
            "批次汇总（规则总结）：",
            f"- 线索：原始 {counts['raw']} 条，清洗后 {counts['clean']} 条",
            f"- 采集：日志 {crawl['total']} 条，成功 {crawl['by_status'].get('ok', 0)} 条，"
            f"失败 {crawl['by_status'].get('failed', 0)} 条",
            f"- 触达：已发 {mails['sent']} 封，回复 {mails['replied']} 封，"
            f"回复率 {mails['reply_rate']}，退订 {mails['unsubscribed']}",
        ]
        if counts["clean"] == 0:
            lines.append("结论：还没有可发送线索，建议先完成采集与清洗。")
        elif mails["sent"] == 0:
            lines.append("结论：线索已就绪但尚未发送，建议先抽检开发信再小批量触达。")
        else:
            lines.append("结论：已形成「采集→清洗→触达」闭环，可继续跟踪回复并复盘话术。")
        return "\n".join(lines), []


__all__ = ["SummarizerAgent"]
