# -*- coding: utf-8 -*-
"""抽取智能体：结构化抽取、去重清洗、邮箱验证。"""

from config import PATHS, ROOT
from lead_agent.Agents.base import ReActAgentBase


class ExtractAgent(ReActAgentBase):
    role = "extract"
    system_prompt = (
        "你是抽取智能体，负责把 raw/ 下的 HTML 转成结构化线索、去重清洗并校验邮箱；"
        "字段缺失就留空，禁止猜测或编造公司信息。"
    )

    def classic_extract_reply(self, text: str, sid: str):
        trace: list[dict] = []
        files = sorted(PATHS["raw"].glob("*.html"))
        lines = [f"抽取与清洗（规则兜底模式）：raw/ 下共 {len(files)} 个 HTML。"]

        if not files:
            lines.append("暂无可抽取页面：先把公开名录页抓取到 raw/，再让我抽取。")
            _, stats = self.use("extract.query_leads", {"limit": 5, "source": "clean"}, sid, trace)
            lines.append(f"当前清洗表有 {stats.get('total', 0)} 条线索。")
            return "\n".join(lines), trace

        found = appended = 0
        for path in files[:5]:
            rel = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
            ok, result = self.use("extract.extract_leads", {"html_path": rel}, sid, trace)
            if ok:
                found += int(result.get("found", 0))
                appended += int(result.get("appended", 0))
        lines.append(f"本次抽取 {min(len(files), 5)} 页：命中 {found} 条，新增 {appended} 条原始线索。")

        ok, cleaned = self.use("extract.clean_leads", {}, sid, trace)
        if ok:
            lines.append(
                f"清洗结果：{cleaned.get('clean', 0)} 条，有效邮箱 {cleaned.get('valid', 0)} 个，"
                f"去重丢弃 {cleaned.get('dropped', 0)} 条。"
            )
            for lead in (cleaned.get("leads") or [])[:3]:
                lines.append(
                    f"- {lead.get('company') or '（未知公司）'}｜{lead.get('website') or '无官网'}"
                    f"｜{lead.get('contact_email') or '无邮箱'}（{lead.get('email_status')}）"
                )
        return "\n".join(lines), trace


__all__ = ["ExtractAgent"]
