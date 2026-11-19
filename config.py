# -*- coding: utf-8 -*-
"""全局配置槽：模型、预算、权限、路径根与网络策略。

约定：
- 所有路径都以项目根为基准，不出现盘符与绝对路径；
- 敏感信息只从 .env 读取，代码里不写死 Key；
- 本模块是全项目唯一的配置入口，其它模块只从这里取常量。
"""

import os
from pathlib import Path

try:  # 未安装 python-dotenv 时也不影响导入
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:  # noqa: BLE001
    pass


def _env_str(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


def _env_int(key: str, default: int) -> int:
    try:
        return int(str(os.getenv(key, default)).strip())
    except (TypeError, ValueError):
        return default


# ------------------------- 路径根 -------------------------

ROOT = Path(__file__).resolve().parent

# 目录：启动时自动创建，避免首次运行报错
_DIR_KEYS = ("data", "memory", "telemetry", "uploads", "leads", "crawl", "raw", "dist")

PATHS = {
    # 目录
    "data": ROOT / "data",
    "memory": ROOT / "data" / "memory",
    "telemetry": ROOT / "data" / "telemetry",
    "uploads": ROOT / "data" / "uploads",
    "leads": ROOT / "data" / "leads",
    "crawl": ROOT / "data" / "crawl",
    "raw": ROOT / "raw",
    "dist": ROOT / "dist",
    "ui": ROOT / "ui",
    # 文件
    "short_term": ROOT / "data" / "memory" / "short_term.jsonl",
    "long_term": ROOT / "data" / "memory" / "long_term.jsonl",
    "telemetry_file": ROOT / "data" / "telemetry" / "live.jsonl",
    "crawl_log": ROOT / "data" / "crawl" / "crawl_log.jsonl",
    "urls": ROOT / "data" / "urls.txt",
    "leads_raw": ROOT / "data" / "leads" / "leads_raw.csv",
    "leads_clean": ROOT / "data" / "leads" / "leads_clean.csv",
    "send_log": ROOT / "data" / "leads" / "send_log.csv",
}

for _key in _DIR_KEYS:
    PATHS[_key].mkdir(parents=True, exist_ok=True)


# ------------------------- 模型 -------------------------

LLM_API_KEY = _env_str("LLM_API_KEY")
LLM_BASE_URL = _env_str("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = _env_str("LLM_MODEL", "deepseek-chat")
LLM_TIMEOUT = _env_int("LLM_TIMEOUT", 60)

# ------------------------- 权限与约束 -------------------------

# plan：写类工具需 confirm=true；auto：不再逐条确认；readonly：只读
AGENT_PERMISSION_MODE = _env_str("AGENT_PERMISSION_MODE", "plan").lower()
# allowlist：仅放行白名单域名（白名单为空时只校验协议）；block：禁止一切外网
TOOL_NET_POLICY = _env_str("TOOL_NET_POLICY", "allowlist").lower()
TOOL_NET_ALLOWLIST = tuple(
    x.strip().lower()
    for x in _env_str("TOOL_NET_ALLOWLIST").split(",")
    if x.strip()
)

# 工具可写的路径根：默认就是项目根，子路径不得逃出这里
TOOL_PATH_ROOTS = tuple(
    Path(item).resolve()
    for item in (
        p.strip()
        for p in _env_str("TOOL_PATH_ROOTS").split(os.pathsep)
        if p.strip()
    )
) or (ROOT,)

MAX_TOOL_CALLS = _env_int("MAX_TOOL_CALLS", 12)  # 单会话工具调用预算
REACT_MAX_ROUNDS = _env_int("REACT_MAX_ROUNDS", 4)  # 单次问答最多工具轮数
CONTEXT_CHAR_BUDGET = _env_int("CONTEXT_CHAR_BUDGET", 6000)

# ------------------------- 发信 -------------------------

DAILY_MAIL_LIMIT = _env_int("DAILY_MAIL_LIMIT", 50)
DRY_RUN_MAIL = _env_str("DRY_RUN_MAIL", "true").lower() in ("1", "true", "yes")
