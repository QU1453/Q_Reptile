# -*- coding: utf-8 -*-
"""线索库 CSV 读写：读、追加、统计，带简化文件锁。

所有路径都相对项目根，不写绝对路径。
"""

import csv
import os
import time
from contextlib import contextmanager
from pathlib import Path

from config import PATHS

# 线索表字段（原始表与清洗表共用）
LEAD_FIELDS = [
    "lead_id",
    "company",
    "country",
    "website",
    "category",
    "contact_email",
    "email_status",
    "source_url",
    "crawled_at",
    "score",
]

# 发送记录字段
SEND_FIELDS = [
    "lead_id",
    "company",
    "email",
    "mail_variant",
    "sent_at",
    "status",
    "follow_up_n",
    "dry_run",
]


@contextmanager
def file_lock(path: Path, timeout: float = 3.0):
    """简化版文件锁：用同名 .lock 文件做进程间互斥。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = Path(str(path) + ".lock")
    deadline = time.time() + timeout
    fd = None
    while True:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.time() > deadline:
                # 认为锁已失效，强行清理后继续等下一轮
                try:
                    lock.unlink()
                except OSError:
                    pass
                deadline = time.time() + timeout
            time.sleep(0.05)
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
        try:
            lock.unlink()
        except OSError:
            pass


def read_csv(path: Path, fields: list[str] | None = None) -> list[dict]:
    """读 CSV 为字典列表；文件不存在时返回空列表。"""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return []
    with file_lock(path):
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            rows = [dict(row) for row in csv.DictReader(f)]
    if fields:
        return [{k: row.get(k, "") for k in fields} for row in rows]
    return rows


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> int:
    """整体覆盖写入 CSV，返回行数。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = fields or (list(rows[0].keys()) if rows else [])
    with file_lock(path):
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            if cols:
                writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                writer.writeheader()
                for row in rows:
                    writer.writerow({k: row.get(k, "") for k in cols})
    return len(rows)


def append_rows(path: Path, rows: list[dict], fields: list[str] | None = None) -> int:
    """追加若干行；文件为空时自动写表头。"""
    path = Path(path)
    if not rows:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    is_empty = (not path.exists()) or path.stat().st_size == 0
    if fields:
        cols = fields
    elif not is_empty:
        cols = list(read_csv(path)[0].keys()) if read_csv(path) else list(rows[0].keys())
    else:
        cols = list(rows[0].keys())
    with file_lock(path):
        with open(path, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            if is_empty:
                writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in cols})
    return len(rows)


def count_rows(path: Path) -> int:
    """统计 CSV 数据行数（不含表头）。"""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return 0
    with file_lock(path):
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            total = sum(1 for _ in reader)
    return max(0, total - 1)


def lead_counts() -> dict:
    """线索库规模概览，供统计接口与总结使用。"""
    return {
        "raw": count_rows(PATHS["leads_raw"]),
        "clean": count_rows(PATHS["leads_clean"]),
        "sent": count_rows(PATHS["send_log"]),
    }


__all__ = [
    "LEAD_FIELDS",
    "SEND_FIELDS",
    "file_lock",
    "read_csv",
    "write_csv",
    "append_rows",
    "count_rows",
    "lead_counts",
]
