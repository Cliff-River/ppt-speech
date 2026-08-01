"""Redis 客户端与进度上报测试。

使用 fakeredis（共享 FakeServer 以支持 pub/sub 跨实例广播）验证：
- Redis 键命名函数正确。
- ProgressReporter 将事件写入 Hash 快照并发布到频道。
- set_terminal_state 正确置终态、设 TTL、发终态事件。
- ping 健康检查。
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
from ppt_speech.server.progress import (
    ProgressReporter,
    Stage,
    TaskStatus,
    set_terminal_state,
)


def _make_redis(server: FakeServer) -> "fakeredis.FakeAsyncRedis":
    return fakeredis.FakeAsyncRedis(server=server, decode_responses=True)


async def _await_message(pubsub, max_tries: int = 30) -> dict | None:
    """轮询获取一条 pub/sub 消息（fakeredis 异步投递存在时序，需重试）。"""
    for _ in range(max_tries):
        msg = await pubsub.get_message(
            ignore_subscribe_messages=True, timeout=0.1
        )
        if msg is not None and msg.get("type") == "message":
            return msg
        await asyncio.sleep(0.02)
    return None


class TestRedisKeys(unittest.TestCase):
    """键命名函数测试。"""

    def test_key_names(self) -> None:
        self.assertEqual(redis_client.task_key("abc"), "ppt_speech:task:abc")
        self.assertEqual(
            redis_client.events_channel("abc"), "ppt_speech:events:abc"
        )
        self.assertEqual(redis_client.task_index_key(), "ppt_speech:tasks:index")


class TestProgressReporter(unittest.IsolatedAsyncioTestCase):
    """ProgressReporter 写入与广播测试。"""

    def setUp(self) -> None:
        self.server = FakeServer()
        self.redis = _make_redis(self.server)

    async def test_reporter_writes_hash_and_publishes(self) -> None:
        """回调写入 Hash 快照并发布事件到频道。"""
        task_id = "t-1"
        reporter = ProgressReporter(task_id, self.redis, total_slides=3, input_filename="in.pptx")

        # 用第二个客户端订阅频道，验证广播
        sub_client = _make_redis(self.server)
        pubsub = sub_client.pubsub()
        await pubsub.subscribe(redis_client.events_channel(task_id))
        await asyncio.sleep(0.05)  # 让订阅生效

        reporter(
            {
                "stage": Stage.SYNTHESIZING,
                "slide_idx": 2,
                "percent": 50.0,
                "eta_seconds": 12.5,
                "message": "合成中",
            }
        )
        # ensure_future 调度的协程需要让出事件循环执行
        await asyncio.sleep(0.1)

        # Hash 快照字段
        data = await self.redis.hgetall(redis_client.task_key(task_id))
        self.assertEqual(data["status"], TaskStatus.PROCESSING)
        self.assertEqual(data["stage"], Stage.SYNTHESIZING)
        self.assertEqual(data["slide_idx"], "2")
        self.assertEqual(data["total_slides"], "3")
        self.assertEqual(data["percent"], "50.0")
        self.assertEqual(data["input_filename"], "in.pptx")

        # 频道收到事件（轮询以应对 fakeredis 异步投递时序）
        message = await _await_message(pubsub)
        self.assertIsNotNone(message)
        event = json.loads(message["data"])
        self.assertEqual(event["stage"], Stage.SYNTHESIZING)
        self.assertEqual(event["task_id"], task_id)

        await pubsub.unsubscribe()
        await pubsub.aclose()


class TestSetTerminalState(unittest.IsolatedAsyncioTestCase):
    """set_terminal_state 终态写入测试。"""

    def setUp(self) -> None:
        self.server = FakeServer()
        self.redis = _make_redis(self.server)

    async def test_completed_sets_fields_ttl_and_publishes(self) -> None:
        task_id = "t-done"
        sub_client = _make_redis(self.server)
        pubsub = sub_client.pubsub()
        await pubsub.subscribe(redis_client.events_channel(task_id))
        await asyncio.sleep(0.05)

        await set_terminal_state(
            task_id,
            self.redis,
            TaskStatus.COMPLETED,
            stage=Stage.COMPLETED,
            message="完成",
            result_ready=True,
            ttl_seconds=600,
            total_slides=4,
            input_filename="in.pptx",
        )

        data = await self.redis.hgetall(redis_client.task_key(task_id))
        self.assertEqual(data["status"], TaskStatus.COMPLETED)
        self.assertEqual(data["percent"], "100.0")
        self.assertEqual(data["result_ready"], "true")
        # TTL 已设
        ttl = await self.redis.ttl(redis_client.task_key(task_id))
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 600)

        # 终态事件已发布
        message = await _await_message(pubsub)
        self.assertIsNotNone(message)
        event = json.loads(message["data"])
        self.assertEqual(event["status"], TaskStatus.COMPLETED)
        self.assertTrue(event["result_ready"])

        await pubsub.unsubscribe()
        await pubsub.aclose()

    async def test_failed_records_error(self) -> None:
        task_id = "t-fail"
        await set_terminal_state(
            task_id,
            self.redis,
            TaskStatus.FAILED,
            stage=Stage.FAILED,
            message="出错",
            error="Traceback: ...",
            ttl_seconds=300,
        )
        data = await self.redis.hgetall(redis_client.task_key(task_id))
        self.assertEqual(data["status"], TaskStatus.FAILED)
        self.assertEqual(data["error"], "Traceback: ...")
        self.assertEqual(data["result_ready"], "false")


class TestPing(unittest.IsolatedAsyncioTestCase):
    """ping 健康检查测试。"""

    async def test_ping_with_fake(self) -> None:
        server = FakeServer()
        redis_client.set_client(
            fakeredis.FakeAsyncRedis(server=server, decode_responses=True)
        )
        try:
            self.assertTrue(await redis_client.ping())
        finally:
            redis_client.set_client(None)


if __name__ == "__main__":
    unittest.main()
