# -*- coding: utf-8 -*-
"""采集工具：URL 生成、批量抓取、抓取状态。

真实抓取逻辑已就位，但**本仓库不主动发起任何请求**；
只有被显式调用且通过约束层网络检查时才会联网。
"""

import hashlib
import json
import time
from urllib.parse import urlparse

import requests

from config import PATHS, ROOT
from lead_agent.core.toolkit.decorator import register

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 LeadAgent/0.1 (student research)"
)
TIMEOUT = 20
RETRY = 3


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _append_log(rec: dict) -> None:
    path = PATHS["crawl_log"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


@register(roles=["collect", "flow"], name="collect.gen_urls")
def gen_urls(base_url: str, list_pattern: str = "", start_page: int = 1, end_page: int = 1) -> dict:
    """按分页规则批量生成待抓 URL（纯字符串拼接，不联网）。"""
    base = str(base_url or "").strip().rstrip("/")
    if not base:
        raise ValueError("base_url 不能为空")

    start, end = int(start_page), int(end_page)
    if end < start:
        start, end = end, start
    end = min(end, start + 500)  # 防误输入造成一次生成过多

    urls: list[str] = []
    for page in range(start, end + 1):
        try:
            path = (list_pattern or "").format(page=page)
        except (KeyError, IndexError, ValueError):
            path = list_pattern or ""
        urls.append(base + path)
    urls = list(dict.fromkeys(urls))

    out = PATHS["urls"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(urls) + "\n", encoding="utf-8")
    return {"count": len(urls), "urls": urls, "saved_to": str(out.relative_to(ROOT))}


def _crawl_one(url: str, session: requests.Session) -> dict:
    """抓单个页面，失败重试 + 指数退避；任何异常都只影响这一条。"""
    last_err = ""
    for attempt in range(1, RETRY + 1):
        try:
            resp = session.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
                timeout=TIMEOUT,
            )
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {resp.status_code}")
            name = hashlib.md5(url.encode("utf-8")).hexdigest()[:16]
            out = PATHS["raw"] / f"{name}.html"
            out.write_text(resp.text, encoding="utf-8", errors="replace")
            return {
                "url": url,
                "status": "ok",
                "http": resp.status_code,
                "file": str(out.relative_to(ROOT)),
                "ts": _now(),
            }
        except Exception as exc:  # noqa: BLE001  失败隔离
            last_err = f"{type(exc).__name__}: {exc}"
            time.sleep(2 ** (attempt - 1))
    return {"url": url, "status": "failed", "error": last_err, "ts": _now()}


@register(roles=["collect", "flow"], name="collect.crawl_pages")
def crawl_pages(urls, limit: int = 10, delay: float = 0.8, confirm: bool = False) -> dict:
    """批量抓取页面并存到 raw/，逐条写 crawl_log.jsonl，失败隔离。"""
    if isinstance(urls, str):
        urls = [line.strip() for line in urls.splitlines() if line.strip()]
    urls = [str(u) for u in (urls or []) if str(u).startswith("http")]
    urls = urls[: max(1, int(limit))]

    ok = failed = 0
    records: list[dict] = []
    session = requests.Session()
    try:
        for url in urls:
            rec = _crawl_one(url, session)
            _append_log(rec)
            records.append(rec)
            if rec["status"] == "ok":
                ok += 1
            else:
                failed += 1
            time.sleep(max(0.0, float(delay)))
    finally:
        session.close()

    return {"total": len(urls), "ok": ok, "failed": failed, "records": records}


@register(roles=["collect", "flow"], name="collect.crawl_status")
def crawl_status() -> dict:
    """读取抓取日志，统计成功/失败数量并列出最近失败。"""
    path = PATHS["crawl_log"]
    if not path.exists():
        return {"total": 0, "by_status": {}, "recent_failed": [], "last_ts": ""}

    stat: dict[str, int] = {}
    failed: list[dict] = []
    last_ts = ""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            status = rec.get("status", "unknown")
            stat[status] = stat.get(status, 0) + 1
            if status != "ok":
                failed.append(rec)
            last_ts = rec.get("ts", last_ts)

    return {
        "total": sum(stat.values()),
        "by_status": stat,
        "recent_failed": failed[-5:],
        "last_ts": last_ts,
    }


__all__ = ["gen_urls", "crawl_pages", "crawl_status"]
