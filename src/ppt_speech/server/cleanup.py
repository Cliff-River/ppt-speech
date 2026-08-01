"""磁盘清理协程模块。

周期性扫描任务工作目录，删除超过结果保留时长的任务子目录，避免磁盘
被已完成任务的输出文件占满。与 Redis 任务键的 TTL 协同：Redis 键到期
后任务状态不可查，磁盘文件由本协程清理。
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from ppt_speech.server.config import ServerConfig


async def cleanup_loop(config: ServerConfig) -> None:
    """周期清理过期任务子目录的协程。

    每 ``config.cleanup_interval_seconds`` 秒扫描一次 ``work_dir``，
    删除 ``mtime`` 早于 ``config.result_ttl_seconds`` 的子目录。

    本协程设计为长期运行（由 FastAPI lifespan 启动），捕获自身异常以避免
    单次清理失败导致协程退出。
    """
    while True:
        try:
            await cleanup_once(config)
        except Exception:
            # 清理失败不应终止协程；下一轮重试。
            pass
        await asyncio.sleep(config.cleanup_interval_seconds)


async def cleanup_once(config: ServerConfig) -> int:
    """执行一次清理，返回已删除的子目录数。"""
    import shutil

    work_dir = config.work_dir
    if not work_dir.exists():
        return 0

    now = time.time()
    cutoff = now - config.result_ttl_seconds
    removed = 0

    for child in work_dir.iterdir():
        if not child.is_dir():
            continue
        try:
            mtime = child.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            try:
                shutil.rmtree(child, ignore_errors=True)
                removed += 1
            except OSError:
                pass

    return removed
