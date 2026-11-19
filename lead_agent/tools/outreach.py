# -*- coding: utf-8 -*-
"""触达工具：写开发信（四段式/可选 LLM 开头）、限速模拟发送、回复统计。"""

import re
import time

from config import DAILY_MAIL_LIMIT, DRY_RUN_MAIL, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, PATHS
from lead_agent.core.toolkit.decorator import register
from lead_agent.tools.catalog import SEND_FIELDS, append_rows, read_csv


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _template_body(company: str, country: str, snippet: str) -> str:
    """四段式模板：业务引用 → 我们能提供 → 具体请求 → 退订与签名。"""
    company = company or "your company"
    market = country or "the overseas market"
    reference = snippet.strip() or f"我们注意到 {company} 在 {market} 市场的业务布局"
    return (
        f"Hi {company} team,\n\n"
        f"1) {reference}，这与我们在跨境供应链/独立站运营上的方向高度契合。\n\n"
        f"2) 我们能提供：面向 {market} 市场的选品与独立站内容方案，"
        f"帮助小型团队以更低成本获得可追踪的询盘。\n\n"
        f"3) 如果方便，我们希望在两周内安排一次 15 分钟的线上沟通，"
        f"先给您一份针对贵司官网的三条改进建议，不收取费用。\n\n"
        f"4) 如不希望继续收到邮件，直接回复 unsubscribe 即可，我们会立即移除。\n\n"
        f"Best regards,\nFelix · 跨境独立站项目组"
    )


def _llm_intro(company: str, country: str, snippet: str) -> str:
    """有 Key 时用模型写一段个性化开头；失败一律回退模板。"""
    if not LLM_API_KEY:
        return ""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=30)
        prompt = (
            f"为 B2B 开发信写一句英文开头，对象公司：{company}，国家/地区：{country}，"
            f"已知信息：{snippet or '无'}。要求：60 词以内、只写开头、不编造事实、不用夸张形容词。"
        )
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:  # noqa: BLE001  任何模型异常都不影响兜底
        return ""


@register(roles=["outreach", "flow"], name="outreach.draft_mail")
def draft_mail(company: str = "", country: str = "", snippet: str = "", language: str = "en") -> dict:
    """按模板生成四段式开发信（含退订行），有模型 Key 时只让模型写开头。"""
    company = (company or "").strip()
    country = (country or "").strip()
    snippet = (snippet or "").strip()

    body = _template_body(company, country, snippet)
    intro = _llm_intro(company, country, snippet)
    if intro:
        body = f"{intro}\n\n{body}"

    subject = f"A quick idea for {company or 'your team'}'s {country or 'overseas'} growth"
    return {
        "company": company,
        "country": country,
        "subject": subject,
        "body": body,
        "language": language,
        "used_llm": bool(intro),
        "chars": len(body),
    }


@register(roles=["outreach", "flow"], name="outreach.send_mails")
def send_mails(limit: int = 5, variant: str = "v1", confirm: bool = False) -> dict:
    """模拟发送（dry_run）并写入 send_log.csv；每日上限与去重在此控制。"""
    leads = read_csv(PATHS["leads_clean"])
    if not leads:
        leads = read_csv(PATHS["leads_raw"])

    sent_before = {r.get("email", "").lower() for r in read_csv(PATHS["send_log"])}
    today = time.strftime("%Y-%m-%d")
    sent_today = sum(
        1 for r in read_csv(PATHS["send_log"]) if (r.get("sent_at") or "").startswith(today)
    )
    quota = max(0, int(DAILY_MAIL_LIMIT) - sent_today)

    ok_rows: list[dict] = []
    skipped = 0
    for lead in leads:
        if len(ok_rows) >= max(0, int(limit)) or len(ok_rows) >= quota:
            break
        email = (lead.get("contact_email") or "").strip().lower()
        status = (lead.get("email_status") or "").strip().lower()
        if not email or status == "invalid" or email in sent_before:
            skipped += 1
            continue
        ok_rows.append(
            {
                "lead_id": lead.get("lead_id", ""),
                "company": lead.get("company", ""),
                "email": email,
                "mail_variant": variant,
                "sent_at": _now(),
                "status": "sent",
                "follow_up_n": "0",
                "dry_run": str(bool(DRY_RUN_MAIL)).lower(),
            }
        )

    append_rows(PATHS["send_log"], ok_rows, SEND_FIELDS)
    return {
        "sent": len(ok_rows),
        "skipped": skipped,
        "quota_left": max(0, quota - len(ok_rows)),
        "dry_run": True,
        "rows": ok_rows,
    }


@register(roles=["outreach", "flow"], name="outreach.mail_stats")
def mail_stats() -> dict:
    """统计发送量、回复量、退信与退订，并计算回复率。"""
    rows = read_csv(PATHS["send_log"])
    stats: dict[str, int] = {}
    for row in rows:
        status = (row.get("status") or "unknown").lower()
        stats[status] = stats.get(status, 0) + 1

    sent = len(rows)
    replied = stats.get("replied", 0)
    return {
        "sent": sent,
        "replied": replied,
        "bounced": stats.get("bounced", 0),
        "unsubscribed": stats.get("unsubscribed", 0),
        "opened": stats.get("opened", 0),
        "reply_rate": round(replied / sent, 4) if sent else 0.0,
        "by_status": stats,
        "daily_limit": DAILY_MAIL_LIMIT,
    }


__all__ = ["draft_mail", "send_mails", "mail_stats"]
