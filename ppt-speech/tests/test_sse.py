"""SSE 事件流测试。

使用 fakeredis（共享 FakeServer）验证 :func:`event_stream`：
- 任务不存在 → 首事件为 FAILED 且流结束。
- 任务已终态（COMPLETED）→ 首事件即终态并结束。
- 处理中任务 → 首事件为快照，后续转发 pub/sub 消息，遇终态结束。
"""

import asyncio
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import fakeredis
from fakeredis import FakeServer

from ppt_speech.server import redis_client
from ppt_speech.server.progress import TaskStatus
from ppt_speech.server.sse import event_stream


def _make_redis(server: FakeServer):
    return fakeredis.FakeAsyncRedis(server=server, decode_responses=True)


def _data_payload(chunk: str) -> dict | None:
    """从 SSE chunk 解析 data 负载；心跳行返回 None。"""
    for line in chunk.splitlines():
        if line.startswith("data: "):
            return json.loads(line[len("data: "):])
    return None


async def _collect(stream, max_chunks: int = 20) -> list[str]:
    chunks: list[str] = []
    async for chunk in stream:
        chunks.append(chunk)
        if len(chunks) >= max_chunks:
            break
    return chunks


class TestEventStream(unittest.IsolatedAsyncioTestCase):
    """event_stream 行为测试。"""

    async def test_not_found_yields_failed(self) -> None:
        """任务不存在 → 首事件 FAILED 并结束。"""
        server = FakeServer()
        redis = _make_redis(server)

        chunks = await _collect(event_stream("no-such-task", redis, heartbeat_seconds=1))
        self.assertEqual(len(chunks), 1)
        event = _data_payload(chunks[0])
        self.assertEqual(event["status"], TaskStatus.FAILED)
        self.assertEqual(event["error"], "not found")

    async def test_terminal_yields_first_and_ends(self) -> None:
        """任务已 COMPLETED → 首事件即终态并结束。"""
        server = FakeServer()
        redis = _make_redis(server)
        task_id = "t-done"
        await redis.hset(
            redis_client.task_key(task_id),
            mapping={
                "status": TaskStatus.COMPLETED,
                "stage": "COMPLETED",
                "percent": "100.0",
                "result_ready": "true",
                "message": "完成",
            },
        )

        chunks = await _collect(event_stream(task_id, redis, heartbeat_seconds=1))
        self.assertEqual(len(chunks), 1)
        event = _data_payload(chunks[0])
        self.assertEqual(event["status"], TaskStatus.COMPLETED)
        self.assertTrue(event["result_ready"])

    async def test_midstream_forwards_pubsub_until_terminal(self) -> None:
        """处理中任务：首事件为快照，转发 pub/sub 消息，遇 COMPLETED 结束。"""
        server = FakeServer()
        redis = _make_redis(server)
        task_id = "t-mid"
        channel = redis_client.events_channel(task_id)
        await redis.hset(
            redis_client.task_key(task_id),
            mapping={
                "status": TaskStatus.PROCESSING,
                "stage": "SYNTHESIZING",
                "slide_idx": "1",
                "total_slides": "2",
                "percent": "25.0",
            },
        )

        async def publish_later() -> None:
            # 等待 event_stream 完成订阅
            await asyncio.sleep(0.2)
            await redis.publish(
                channel,
                json.dumps({"status": "PROCESSING", "stage": "EMBEDDING", "percent": 75.0}),
            )
            await asyncio.sleep(0.1)
            await redis.publish(
                channel,
                json.dumps(
                    {
                        "status": TaskStatus.COMPLETED,
                        "stage": "COMPLETED",
                        "percent": 100.0,
                        "result_ready": True,
                    }
                ),
            )

        task = asyncio.create_task(publish_later())
        chunks = await _collect(event_stream(task_id, redis, heartbeat_seconds=2))
        await task

        # 至少：首快照 + EMBEDDING + COMPLETED
        events = [e for e in (_data_payload(c) for c in chunks) if e]
        statuses = [e.get("status") for e in events]
        self.assertEqual(statuses[0], TaskStatus.PROCESSING)
        self.assertIn(TaskStatus.COMPLETED, statuses)
        self.assertEqual(statuses[-1], TaskStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
