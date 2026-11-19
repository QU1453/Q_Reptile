# -*- coding: utf-8 -*-
"""tools 门面：re-export 所有工具函数（导入即触发 @register）。"""

from lead_agent.tools.collect import crawl_pages, crawl_status, gen_urls
from lead_agent.tools.document import parse_document
from lead_agent.tools.extract import clean_leads, extract_leads, query_leads
from lead_agent.tools.outreach import draft_mail, mail_stats, send_mails
from lead_agent.tools.verify import verify_emails

__all__ = [
    "gen_urls",
    "crawl_pages",
    "crawl_status",
    "parse_document",
    "extract_leads",
    "clean_leads",
    "query_leads",
    "verify_emails",
    "draft_mail",
    "send_mails",
    "mail_stats",
]
