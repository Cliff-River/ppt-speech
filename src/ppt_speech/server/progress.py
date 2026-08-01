"""进度上报模块。

定义任务状态机、进度事件结构以及 :class:`ProgressReporter`——后者作为
:func:`ppt_speech.pipeline.process_slides` 的 ``on_progress`` 回调实现，
将 pipeline 产出的进度事件写入 Redis（Hash 快照 + pub/sub 广播）。

设计要点
========
- :class:`ProgressReporter.__call__` 是**同步**可调用对象，与 pipeline 调用
  点（同步代码）匹配。Redis 写入为异步操作，故内部用
  :func:`asyncio.ensure_future` 将其调度到当前事件循环，不在回调中 ``await``。
- reporter 运行于 ``run_task`` 的 asyncio 任务内，与 pipeline 共享同一事件
  循环，``ensure_future`` 可安全调度。
- 事件 JSON 经 pub/sub 频道广播，SSE 订阅者（含重连客户端）即时收到；
  Hash 快照供 SSE 首次连接时续看最新状态。
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional, TypedDict

from redis.asyncio import Redis

from ppt_speech.pipeline import (
    STAGE_COMPLETED,
    STAGE_EMBEDDING,
    STAGE_READING_NOTES,
    STAGE_SAVING,
    STAGE_SETTING_TRANSITION,
    STAGE_SYNTHESIZING,
    STAGE_VALIDATING,
)
from ppt_speech.server import redis_client


class Stage:
    """处理阶段常量（复用 pipeline 的字符串语义，并补充服务端专属状态）。"""

    VALIDATING = STAGE_VALIDATING
    READING_NOTES = STAGE_READING_NOTES
    SYNTHESIZING = STAGE_SYNTHESIZING
    EMBEDDING = STAGE_EMBEDDING
    SETTING_TRANSITION = STAGE_SETTING_TRANSITION
    SAVING = STAGE_SAVING
    COMPLETED = STAGE_COMPLETED
    FAILED = "FAILED"


class TaskStatus:
    """任务生命周期状态。"""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    @classmethod
    def is_terminal(cls, status: Optional[str]) -> bool:
        """判断状态是否为终态（COMPLETED / FAILED）。"""
        return status in (cls.COMPLETED, cls.FAILED)


class ProgressEvent(TypedDict, total=False):
    """完整的进度事件结构（pipeline 子集 + 服务端补充字段）。"""

    task_id: str
    status: str
    stage: str
    slide_idx: int
    total_slides: int
    percent: float
    eta_seconds: Optional[float]
    message: str
    timestamp: float
    error: Optional[str]
    result_ready: bool


def _now() -> float:
    return time.time()


class ProgressReporter:
    """pipeline 进度回调的服务端实现。

    将 pipeline 传入的 ``ProcessProgressEvent`` 补齐服务端字段后，写入
    Redis 任务 Hash（最新快照）并发布到事件频道。同步调用语义，内部异步
    写入经 :func:`asyncio.ensure_future` 调度。

    Args:
        task_id: 任务 ID。
        redis: Redis 客户端（可为 fakeredis）。
        total_slides: 幻灯片总页数。
        input_filename: 输入文件名（用于快照展示）。
    """

    def __init__(
        self,
        task_id: str,
        redis: Redis,
        total_slides: int,
        input_filename: str,
    ) -> None:
        self._task_id = task_id
        self._redis = redis
        self._total_slides = total_slides
        self._input_filename = input_filename

    def __call__(self, event: dict) -> None:
        """pipeline 回调入口：补字段、写 Hash、发 pub/sub（非阻塞调度）。"""
        full: dict[str, Any] = {
            "task_id": self._task_id,
            "status": TaskStatus.PROCESSING,
            "timestamp": _now(),
            "total_slides": self._total_slides,
            "input_filename": self._input_filename,
        }
        full.update(event)
        # 同步调度异步写入，避免在 pipeline 同步调用点 await。
        try:
            asyncio.ensure_future(self._persist(full))
        except RuntimeError:
            # 无运行中事件循环（极端情况下）时降级为直接丢弃，避免崩溃主流程。
            pass

    async def _persist(self, event: dict) -> None:
        """将事件写入 Redis Hash 快照并发布到频道。"""
        key = redis_client.task_key(self._task_id)
        channel = redis_client.events_channel(self._task_id)

        mapping: dict[str, str] = {
            "task_id": self._task_id,
            "status": str(event.get("status", TaskStatus.PROCESSING)),
            "stage": str(event.get("stage", "")),
            "slide_idx": str(event.get("slide_idx", 0)),
            "total_slides": str(event.get("total_slides", self._total_slides)),
            "percent": str(event.get("percent", 0.0)),
            "eta_seconds": "" if event.get("eta_seconds") is None else str(event["eta_seconds"]),
            "message": str(event.get("message", "")),
            "input_filename": self._input_filename,
            "updated_at": str(event.get("timestamp", _now())),
            "error": str(event.get("error", "") or ""),
            "result_ready": str(event.get("result_ready", False)).lower(),
        }
        try:
            await self._redis.hset(key, mapping=mapping)
            await self._redis.publish(channel, json.dumps(event, ensure_ascii=False))
        except Exception:
            # Redis 写入失败不应阻断 pipeline 主流程；SSE 仍可从 Hash 续看。
            pass


async def set_terminal_state(
    task_id: str,
    redis: Redis,
    status: str,
    *,
    stage: str = "",
    message: str = "",
    error: str = "",
    result_ready: bool = False,
    ttl_seconds: int = 3600,
    total_slides: int = 0,
    input_filename: str = "",
) -> None:
    """将任务置为终态：更新 Hash、设 TTL、发布终态事件。

    Args:
        task_id: 任务 ID。
        redis: Redis 客户端。
        status: 终态（COMPLETED / FAILED）。
        stage: 阶段（COMPLETED / FAILED）。
        message: 终态消息。
        error: 错误堆栈（FAILED 时）。
        result_ready: 结果是否可下载。
        ttl_seconds: 终态后保留时长（秒）。
        total_slides: 总页数。
        input_filename: 输入文件名。
    """
    now = _now()
    key = redis_client.task_key(task_id)
    channel = redis_client.events_channel(task_id)

    mapping: dict[str, str] = {
        "status": status,
        "stage": stage or status,
        "message": message,
        "error": error,
        "result_ready": str(result_ready).lower(),
        "updated_at": str(now),
    }
    if total_slides:
        mapping["total_slides"] = str(total_slides)
    if input_filename:
        mapping["input_filename"] = input_filename
    if status == TaskStatus.COMPLETED:
        mapping["percent"] = "100.0"

    event: dict[str, Any] = {
        "task_id": task_id,
        "status": status,
        "stage": stage or status,
        "message": message,
        "error": error or None,
        "result_ready": result_ready,
        "timestamp": now,
    }

    await redis.hset(key, mapping=mapping)
    await redis.expire(key, ttl_seconds)
    await redis.publish(channel, json.dumps(event, ensure_ascii=False))
