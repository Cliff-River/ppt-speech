"""Server-Sent Events 流生成模块。

提供 :func:`event_stream` 异步生成器，供 FastAPI ``StreamingResponse`` 推送
实时进度事件。流程：

1. ``HGETALL`` 读取任务最新快照 → 立即 yield 首事件（解决客户端重连续看）。
2. 若任务已终态 → yield 后结束。
3. 否则订阅 ``ppt_speech:events:{task_id}`` 频道，转发 pub/sub 消息，
   遇终态事件结束。
4. 周期性 yield ``: keepalive`` 心跳，防止代理/浏览器断开空闲连接。
5. ``try/finally`` 退订并关闭 pubsub，妥善处理客户端断开。
6. Redis 异常时 yield 一条 FAILED 事件后结束。

事件格式遵循 SSE 规范：``data: {json}\\n\\n``，心跳为注释行 ``: keepalive\\n\\n``。
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Optional

from redis.asyncio import Redis

from ppt_speech.server import redis_client
from ppt_speech.server.progress import TaskStatus


def _format_data(payload: dict[str, Any]) -> str:
    """将字典格式化为 SSE ``data:`` 行。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _hash_to_event(task_id: str, data: dict[str, str]) -> dict[str, Any]:
    """将 Redis Hash 快照转换为事件字典。"""
    eta_raw = data.get("eta_seconds", "")
    eta: Optional[float] = float(eta_raw) if eta_raw else None
    try:
        percent = float(data.get("percent", "0.0"))
    except ValueError:
        percent = 0.0
    try:
        slide_idx = int(data.get("slide_idx", "0"))
    except ValueError:
        slide_idx = 0
    try:
        total_slides = int(data.get("total_slides", "0"))
    except ValueError:
        total_slides = 0

    return {
        "task_id": task_id,
        "status": data.get("status", ""),
        "stage": data.get("stage", ""),
        "slide_idx": slide_idx,
        "total_slides": total_slides,
        "percent": percent,
        "eta_seconds": eta,
        "message": data.get("message", ""),
        "error": data.get("error", "") or None,
        "result_ready": data.get("result_ready", "false").lower() == "true",
    }


async def event_stream(
    task_id: str,
    redis: Redis,
    heartbeat_seconds: int = 15,
) -> AsyncIterator[str]:
    """生成任务进度的 SSE 事件流。

    Args:
        task_id: 任务 ID。
        redis: Redis 客户端。
        heartbeat_seconds: 心跳间隔（秒）。

    Yields:
        SSE 格式字符串（``data: ...\\n\\n`` 或 ``: keepalive\\n\\n``）。
    """
    key = redis_client.task_key(task_id)
    channel = redis_client.events_channel(task_id)

    # 1) 首次读取快照，立即推送（重连续看）。
    try:
        data = await redis.hgetall(key)
    except Exception:
        yield _format_data(
            {
                "task_id": task_id,
                "status": TaskStatus.FAILED,
                "stage": TaskStatus.FAILED,
                "message": "读取任务状态失败（Redis 不可用）",
                "error": "redis unavailable",
            }
        )
        return

    if not data:
        # 任务不存在或已过期。
        yield _format_data(
            {
                "task_id": task_id,
                "status": TaskStatus.FAILED,
                "stage": TaskStatus.FAILED,
                "message": "任务不存在或已过期",
                "error": "not found",
            }
        )
        return

    first_event = _hash_to_event(task_id, data)
    yield _format_data(first_event)

    # 2) 已终态 → 结束。
    if TaskStatus.is_terminal(first_event.get("status")):
        return

    # 3) 订阅事件频道，转发实时消息。
    pubsub = redis.pubsub()
    try:
        await pubsub.subscribe(channel)
        while True:
            try:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=heartbeat_seconds,
                )
            except Exception:
                # Redis 异常：推送 FAILED 后结束。
                yield _format_data(
                    {
                        "task_id": task_id,
                        "status": TaskStatus.FAILED,
                        "stage": TaskStatus.FAILED,
                        "message": "实时事件流中断（Redis 不可用）",
                        "error": "redis unavailable",
                    }
                )
                return

            if message is None:
                # 超时无消息 → 心跳。
                yield ": keepalive\n\n"
                continue

            if message.get("type") != "message":
                continue

            raw = message.get("data")
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")

            yield f"data: {raw}\n\n"

            # 解析判断是否终态。
            try:
                event = json.loads(raw)
            except (TypeError, ValueError):
                continue
            if TaskStatus.is_terminal(event.get("status")):
                return
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
        except Exception:
            pass
