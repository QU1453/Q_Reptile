# -*- coding: utf-8 -*-
"""FastAPI 入口：/api/ask 等路由 + 托管 ui/ 静态资源。

启动（不要在本仓库自动执行）：
    uvicorn server:app --host 127.0.0.1 --port 8000
"""

import json
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import (
    AGENT_PERMISSION_MODE,
    DAILY_MAIL_LIMIT,
    DRY_RUN_MAIL,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    MAX_TOOL_CALLS,
    PATHS,
    ROOT,
    TOOL_NET_ALLOWLIST,
    TOOL_NET_POLICY,
)
from lead_agent.Agents import Supervisor
from lead_agent.core.dispatch.orchestrator import Orchestrator
from lead_agent.core.telemetry import live
from lead_agent.tools.catalog import lead_counts
from lead_agent.tools.extract import query_leads

VERSION = "20261119"

app = FastAPI(title="AI 爬虫自动化获客", description="第二组作业 · 多智能体获客骨架", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/ui", StaticFiles(directory=str(PATHS["ui"])), name="ui")

SUPERVISOR = Supervisor()
ORCHESTRATOR = Orchestrator(SUPERVISOR)


class AskIn(BaseModel):
    text: str
    session_id: str | None = None


@app.post("/api/ask")
def ask(payload: AskIn) -> dict:
    """一次问答：Supervisor 规则路由 → 业务智能体 → 统一结构。"""
    if not (payload.text or "").strip():
        return {"answer": "请输入内容。", "trace": [], "agent": "supervisor"}
    return ORCHESTRATOR.handle(payload.text, payload.session_id)


@app.get("/api/stats")
def stats() -> dict:
    """看板数据：线索、采集、发送、预算与策略。"""
    data = SUPERVISOR.stats()
    data["leads"] = lead_counts()
    return data


@app.get("/api/leads")
def leads(limit: int = 20, source: str = "clean", status: str = "all") -> dict:
    """读取线索表（默认清洗表）。"""
    return query_leads(limit=limit, source=source, status=status)


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    """上传 csv/txt/md 到 data/uploads（只保留文件名，防目录穿越）。"""
    name = Path(file.filename or "upload.bin").name
    target = PATHS["uploads"] / name
    content = await file.read()
    target.write_bytes(content)
    live.log("upload", filename=name, size=len(content))
    return {"ok": True, "filename": name, "size": len(content)}


# ------------------------- 配置读写 -------------------------

ENV_WRITABLE = (
    "LLM_MODEL",
    "LLM_BASE_URL",
    "AGENT_PERMISSION_MODE",
    "TOOL_NET_POLICY",
    "TOOL_NET_ALLOWLIST",
    "MAX_TOOL_CALLS",
    "DAILY_MAIL_LIMIT",
    "DRY_RUN_MAIL",
)


class ConfigIn(BaseModel):
    values: dict[str, str] = {}


@app.get("/api/config")
def read_config() -> dict:
    """返回可写配置的当前值（API Key 只报是否已配置，不回传明文）。"""
    return {
        "env": {
            "LLM_MODEL": LLM_MODEL,
            "LLM_BASE_URL": LLM_BASE_URL,
            "LLM_API_KEY_SET": bool(LLM_API_KEY),
            "AGENT_PERMISSION_MODE": AGENT_PERMISSION_MODE,
            "TOOL_NET_POLICY": TOOL_NET_POLICY,
            "TOOL_NET_ALLOWLIST": ",".join(TOOL_NET_ALLOWLIST),
            "MAX_TOOL_CALLS": str(MAX_TOOL_CALLS),
            "DAILY_MAIL_LIMIT": str(DAILY_MAIL_LIMIT),
            "DRY_RUN_MAIL": "true" if DRY_RUN_MAIL else "false",
        },
        "writable": list(ENV_WRITABLE),
        "need_restart": True,
    }


@app.post("/api/config")
def save_config(payload: ConfigIn) -> dict:
    """白名单内的配置写回项目 .env；不热更新，需重启服务。"""
    env_path = ROOT / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    updated, added = [], []

    for key, raw in (payload.values or {}).items():
        key = str(key).strip().upper()
        if key not in ENV_WRITABLE:
            continue
        value = str(raw).strip().replace("\n", "").replace("\r", "")

        index = None
        for i, line in enumerate(lines):
            if "=" in line and line.split("=", 1)[0].strip() == key:
                index = i
                break

        if index is None:
            lines.append(f"{key}={value}")
            added.append(key)
        elif lines[index].split("=", 1)[1].strip() != value:
            lines[index] = f"{key}={value}"
            updated.append(key)

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    live.log("config_save", updated=updated, added=added)
    return {"ok": True, "updated": updated, "added": added, "need_restart": True}


@app.get("/api/debug/tail")
def debug_tail(n: int = 30) -> dict:
    """读取遥测日志最后 n 条，供调试面板展示。"""
    path = PATHS["telemetry_file"]
    if not path.exists():
        return {"events": []}
    count = max(1, min(int(n), 200))
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-count:]
    events = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {"events": events}


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """返回单页 UI，静态资源带 ?v= 版本号。"""
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html.replace("{{V}}", VERSION))


if __name__ == "__main__":  # 手动运行时使用；正常请用 uvicorn server:app
    import uvicorn

    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
