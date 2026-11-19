# -*- coding: utf-8 -*-
"""邮箱验证：语法校验 + 常见无效域判定，不调用任何外部 API。"""

import re

from lead_agent.core.toolkit.decorator import register

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")

# 明显无效或示例用域名
INVALID_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "test.com",
    "invalid.com",
    "localhost",
    "domain.com",
    "email.com",
    "yourdomain.com",
}

# 免费邮箱：对 B2B 获客而言属于「可用但风险偏高」
FREE_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "qq.com",
    "163.com",
    "126.com",
    "foxmail.com",
    "sina.com",
}


def _check_one(email: str) -> dict:
    email = (email or "").strip().lower()
    if not email:
        return {"email": email, "status": "invalid", "reason": "空地址"}
    if len(email) > 254 or not EMAIL_RE.match(email):
        return {"email": email, "status": "invalid", "reason": "语法不合法"}

    domain = email.rsplit("@", 1)[-1]
    if domain in INVALID_DOMAINS or domain.endswith(".test") or domain.endswith(".invalid"):
        return {"email": email, "status": "invalid", "reason": "示例/保留域名"}
    if domain in FREE_DOMAINS:
        return {"email": email, "status": "risky", "reason": "免费邮箱，非企业域"}
    local = email.split("@", 1)[0]
    if local in ("noreply", "no-reply", "postmaster", "abuse"):
        return {"email": email, "status": "risky", "reason": "不可触达的系统地址"}
    return {"email": email, "status": "valid", "reason": "通过语法与域名检查"}


@register(roles=["extract", "flow"], name="verify.verify_emails")
def verify_emails(emails) -> dict:
    """批量校验邮箱语法与域名，返回 valid / risky / invalid 三类结果。"""
    if isinstance(emails, str):
        emails = [x.strip() for x in re.split(r"[,;\s]+", emails) if x.strip()]
    items = [_check_one(str(e)) for e in (emails or [])]
    # 同一地址只判一次
    unique: dict[str, dict] = {}
    for item in items:
        unique.setdefault(item["email"], item)
    results = list(unique.values())

    stats = {"valid": 0, "risky": 0, "invalid": 0}
    for item in results:
        stats[item["status"]] = stats.get(item["status"], 0) + 1
    return {"total": len(results), **stats, "results": results}


__all__ = ["verify_emails"]
