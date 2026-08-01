"""任务生命周期测试（TaskManager）。

用 fakeredis + 临时 work_dir，mock 掉 ``Presentation`` 与 ``process_slides``，
验证：
- ``create_task`` 校验失败抛 ValueError 且不注册任务。
- 成功路径：run_task 置 COMPLETED、result_ready、删 input、设 TTL。
- 异常路径：run_task 置 FAILED、记录 error、发终态事件。
- get_task / list_tasks 查询。
"""

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import fakeredis
from fakeredis import FakeServer

from ppt_speech.server import redis_client
from ppt_speech.server.config import ServerConfig
from ppt_speech.server.progress import TaskStatus
from ppt_speech.server.tasks import TaskManager

_VALID_PARAMS = {
    "voice_name": "zh-CN-XiaoxiaoNeural",
    "speech_rate": "+0%",
    "auto_advance": True,
    "auto_advance_delay": 2.0,
}


def _make_config(work_dir: Path) -> ServerConfig:
    return ServerConfig(
        redis_host="localhost",
        redis_port=6379,
        work_dir=work_dir,
        result_ttl_seconds=600,
    )


async def _wait_terminal(manager: TaskManager, task_id: str, timeout: float = 5.0):
    """轮询任务直至终态或超时。"""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        task = await manager.get_task(task_id)
        if task and TaskStatus.is_terminal(task.get("status")):
            return task
        await asyncio.sleep(0.05)
    return await manager.get_task(task_id)


class TestTaskManagerLifecycle(unittest.IsolatedAsyncioTestCase):
    """TaskManager 创建/运行/查询测试。"""

    def setUp(self) -> None:
        self.server = FakeServer()
        self.redis = fakeredis.FakeAsyncRedis(
            server=self.server, decode_responses=True
        )
        self.work_dir = Path(tempfile.mkdtemp())
        self.config = _make_config(self.work_dir)
        self.manager = TaskManager(self.redis, self.config)

    def tearDown(self) -> None:
        import shutil

        if self.work_dir.exists():
            shutil.rmtree(self.work_dir, ignore_errors=True)

    async def test_create_invalid_config_raises(self) -> None:
        """非法 voice_name 抛 ValueError，不注册任务、清理目录。"""
        with self.assertRaises(ValueError):
            await self.manager.create_task(
                b"fake", "input.pptx", {**_VALID_PARAMS, "voice_name": "bad-voice"}
            )
        # 无任务注册
        ids = await self.redis.smembers(redis_client.task_index_key())
        self.assertEqual(ids, set())
        # work_dir 下无残留子目录
        self.assertEqual(list(self.work_dir.iterdir()), [])

    @patch("ppt_speech.server.tasks.Presentation")
    @patch("ppt_speech.server.tasks.process_slides", new_callable=AsyncMock)
    async def test_success_path(
        self, mock_process: AsyncMock, mock_presentation: MagicMock
    ) -> None:
        """成功路径：COMPLETED、result_ready、删 input、设 TTL。"""
        mock_prs = MagicMock()
        mock_prs.slides = [MagicMock()]
        mock_presentation.return_value = mock_prs

        task_id = await self.manager.create_task(
            b"fake pptx", "input.pptx", _VALID_PARAMS
        )

        # 初始为 PENDING
        task = await self.manager.get_task(task_id)
        self.assertEqual(task["status"], TaskStatus.PENDING)

        # 等待终态
        task = await _wait_terminal(self.manager, task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task["status"], TaskStatus.COMPLETED)
        self.assertEqual(task["result_ready"], "true")
        self.assertEqual(task["percent"], "100.0")

        # process_slides 被调用（带 on_progress 回调）
        mock_process.assert_called_once()
        self.assertEqual(mock_process.call_args.args[0], mock_prs)

        # input.pptx 已删除，output.pptx 不要求存在（mock 未生成）
        input_file = self.manager.task_dir(task_id) / "input.pptx"
        self.assertFalse(input_file.exists())

        # TTL 已设
        ttl = await self.redis.ttl(redis_client.task_key(task_id))
        self.assertGreater(ttl, 0)

    @patch("ppt_speech.server.tasks.Presentation")
    @patch("ppt_speech.server.tasks.process_slides", new_callable=AsyncMock)
    async def test_failure_path(
        self, mock_process: AsyncMock, mock_presentation: MagicMock
    ) -> None:
        """异常路径：FAILED、error 非空。"""
        mock_prs = MagicMock()
        mock_prs.slides = [MagicMock()]
        mock_presentation.return_value = mock_prs
        mock_process.side_effect = RuntimeError("合成爆炸")

        task_id = await self.manager.create_task(
            b"fake pptx", "input.pptx", _VALID_PARAMS
        )

        task = await _wait_terminal(self.manager, task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task["status"], TaskStatus.FAILED)
        self.assertIn("合成爆炸", task["error"])

    @patch("ppt_speech.server.tasks.Presentation")
    @patch("ppt_speech.server.tasks.process_slides", new_callable=AsyncMock)
    async def test_list_tasks(
        self, mock_process: AsyncMock, mock_presentation: MagicMock
    ) -> None:
        """list_tasks 返回已注册任务。"""
        mock_presentation.return_value = MagicMock(slides=[MagicMock()])
        await self.manager.create_task(b"fake", "input.pptx", _VALID_PARAMS)

        tasks = await self.manager.list_tasks()
        self.assertEqual(len(tasks), 1)

    async def test_result_path_and_is_ready(self) -> None:
        """is_result_ready 判断逻辑。"""
        task_id = "manual"
        await self.redis.hset(
            redis_client.task_key(task_id),
            mapping={"status": TaskStatus.COMPLETED, "result_ready": "true"},
        )
        task = await self.manager.get_task(task_id)
        self.assertTrue(self.manager.is_result_ready(task))

        # 写一个真实输出文件验证 result_path
        out = self.manager.result_path(task_id)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"output")
        self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
