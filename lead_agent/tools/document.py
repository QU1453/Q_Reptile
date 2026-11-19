# -*- coding: utf-8 -*-
"""文档工具：读取 data/uploads 下的 csv / txt / md。"""

from pathlib import Path

from config import PATHS
from lead_agent.core.toolkit.decorator import register

ALLOWED_SUFFIX = {".csv", ".txt", ".md"}


@register(roles=["*"], name="document.parse_document")
def parse_document(filename: str, max_chars: int = 3000) -> dict:
    """读取上传的 csv/txt/md 文件，返回字符数与内容预览（不联网）。"""
    name = Path(str(filename)).name  # 只允许 uploads 下的文件名，防目录穿越
    path = PATHS["uploads"] / name
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"data/uploads 下没有文件：{name}")

    suffix = path.suffix.lower()
    if suffix not in ALLOWED_SUFFIX:
        raise ValueError(f"仅支持 csv/txt/md，收到：{suffix or '无后缀'}")

    limit = max(200, int(max_chars))
    if suffix == ".csv":
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        header = lines[0] if lines else ""
        preview = "\n".join(lines[:30])[:limit]
        return {
            "filename": name,
            "rows": max(0, len(lines) - 1),
            "header": header,
            "chars": len(preview),
            "preview": preview,
        }

    text = path.read_text(encoding="utf-8", errors="replace")
    preview = text[:limit]
    return {
        "filename": name,
        "rows": len(text.splitlines()),
        "header": "",
        "chars": len(preview),
        "preview": preview,
    }


__all__ = ["parse_document"]
