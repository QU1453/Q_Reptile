# -*- coding: utf-8 -*-
"""抽取与清洗工具：HTML → 线索表，去重规范化，查询线索。"""

import hashlib
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from config import PATHS, ROOT
from lead_agent.core.toolkit.decorator import register
from lead_agent.tools.catalog import (
    LEAD_FIELDS,
    append_rows,
    read_csv,
    write_csv,
)
from lead_agent.tools.verify import verify_emails

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
MAX_EMAILS_PER_PAGE = 5


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _resolve_html(html_path: str) -> Path:
    path = Path(str(html_path))
    if path.is_absolute():
        return path
    candidate = ROOT / path
    if candidate.exists():
        return candidate
    return PATHS["raw"] / path.name


def _normalize_website(url: str) -> str:
    """去协议、去 www、去尾部斜杠、转小写。"""
    url = (url or "").strip().lower()
    if not url:
        return ""
    if "://" in url:
        netloc = urlparse(url).netloc
    else:
        netloc = url.split("/")[0]
    netloc = netloc.split("@")[-1].split(":")[0]
    return netloc[4:] if netloc.startswith("www.") else netloc


def _lead_id(company: str, email: str) -> str:
    key = f"{(company or '').strip().lower()}|{(email or '').strip().lower()}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()[:12]


@register(roles=["extract", "flow"], name="extract.extract_leads")
def extract_leads(html_path: str) -> dict:
    """从单个 HTML 提取公司名、邮箱、官网，追加写入 leads_raw.csv。"""
    path = _resolve_html(html_path)
    if not path.exists():
        raise FileNotFoundError(f"找不到 HTML：{html_path}")

    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # 公司名：优先 og:site_name，其次 title 首段
    company = ""
    og = soup.find("meta", attrs={"property": "og:site_name"})
    if og and og.get("content"):
        company = og["content"].strip()
    if not company and soup.title and soup.title.string:
        company = soup.title.string.split("|")[0].split("-")[0].strip()

    # 官网：正文里第一个外部 http 链接的域名
    website = ""
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("http") and "mailto:" not in href:
            website = _normalize_website(href)
            if website:
                break

    # 邮箱：页面全文去重，最多取 5 个
    text = soup.get_text(" ", strip=True)
    emails = list(dict.fromkeys(EMAIL_RE.findall(text)))[:MAX_EMAILS_PER_PAGE]

    ts = _now()
    rows: list[dict] = []
    if company or emails:
        for email in emails or [""]:
            rows.append(
                {
                    "lead_id": _lead_id(company, email),
                    "company": company,
                    "country": "",
                    "website": website,
                    "category": "",
                    "contact_email": email.lower(),
                    "email_status": "unknown",
                    "source_url": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else "",
                    "crawled_at": ts,
                    "score": "",
                }
            )

    # 与已有原始表按 lead_id 去重追加
    exists = {r.get("lead_id") for r in read_csv(PATHS["leads_raw"], LEAD_FIELDS)}
    new_rows = [r for r in rows if r["lead_id"] not in exists]
    append_rows(PATHS["leads_raw"], new_rows, LEAD_FIELDS)

    return {
        "file": path.name,
        "found": len(rows),
        "appended": len(new_rows),
        "leads": new_rows[:10],
    }


@register(roles=["extract", "flow"], name="extract.clean_leads")
def clean_leads() -> dict:
    """去重 + 官网归一化 + 邮箱格式校验，输出 leads_clean.csv。"""
    raw = read_csv(PATHS["leads_raw"], LEAD_FIELDS)

    result = verify_emails([r.get("contact_email", "") for r in raw if r.get("contact_email")])
    status_map = {item["email"]: item["status"] for item in result["results"]}

    seen: set[str] = set()
    cleaned: list[dict] = []
    dropped = 0
    for row in raw:
        company = (row.get("company") or "").strip()
        country = (row.get("country") or "").strip().upper()
        email = (row.get("contact_email") or "").strip().lower()
        key = f"{company.lower()}|{country}" if company else f"email|{email}"
        if not key or key in seen:
            dropped += 1
            continue
        seen.add(key)

        row["company"] = company
        row["country"] = country
        row["website"] = _normalize_website(row.get("website", ""))
        row["contact_email"] = email
        row["email_status"] = status_map.get(email, "unknown") if email else "unknown"
        cleaned.append(row)

    write_csv(PATHS["leads_clean"], cleaned, LEAD_FIELDS)
    valid = sum(1 for r in cleaned if r["email_status"] == "valid")
    return {
        "raw": len(raw),
        "clean": len(cleaned),
        "dropped": dropped,
        "valid": valid,
        "leads": cleaned[:5],
    }


@register(roles=["extract", "outreach", "flow"], name="extract.query_leads")
def query_leads(limit: int = 20, source: str = "clean", status: str = "all") -> dict:
    """查询线索表；source=clean/raw，status=all/valid/risky/invalid。"""
    path = PATHS["leads_clean"] if source == "clean" else PATHS["leads_raw"]
    if not path.exists() and source == "clean":
        path = PATHS["leads_raw"]
        source = "raw"

    rows = read_csv(path, LEAD_FIELDS)
    if status and status != "all":
        rows = [r for r in rows if (r.get("email_status") or "") == status]

    n = max(0, int(limit))
    return {
        "source": source,
        "total": len(rows),
        "count": min(len(rows), n),
        "leads": rows[:n],
    }


__all__ = ["extract_leads", "clean_leads", "query_leads"]
