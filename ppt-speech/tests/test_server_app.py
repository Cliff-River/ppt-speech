"""FastAPI 服务端路由测试。

使用 FastAPI ``TestClient`` + ``dependency_overrides`` 注入伪造的
``TaskManager`` / Redis / 配置，验证各端点的状态码与响应：
- 健康检查（200 / 503）。
- 创建任务（202 / 400 / 422 / 413）。
- 查询任务（200 / 404）、列表。
- 下载结果（200 / 409 / 404）。

SSE ``/progress`` 端点的流行为由 ``test_sse.py`` 直接测试 ``event_stream`` 覆盖。
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi.testclient import TestClient

from ppt_speech.server import redis_client
from ppt_speech.server.app import app, get_config, get_manager, get_redis_dep
from ppt_speech.server.config import ServerConfig
from ppt_speech.server.progress import TaskStatus
from ppt_speech.server.tasks import TaskManager

_PPTX_MEDIA = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)


class FakeTaskManager:
    """可控行为的伪 TaskManager。"""

    def __init__(self, work_dir: Path) -> None:
        self.work_dir = work_dir
        self.tasks: dict[str, dict] = {}
        self.created: list[tuple] = []
        self._counter = 0

    async def create_task(self, file_bytes: bytes, filename: str, params: dict) -> str:
        if params.get("voice_name") == "bad-voice":
            raise ValueError("语音名称格式错误: 'bad-voice'")
        task_id = f"fake-{self._counter}"
        self._counter += 1
        self.created.append((filename, params))
        self.tasks[task_id] = {
            "task_id": task_id,
            "status": TaskStatus.PENDING,
            "stage": "VALIDATING",
            "percent": "0.0",
            "result_ready": "false",
            "input_filename": filename,
        }
        return task_id

    async def get_task(self, task_id: str):
        return self.tasks.get(task_id)

    async def list_tasks(self):
        return list(self.tasks.values())

    def is_result_ready(self, task: dict) -> bool:
        return task.get("status") == TaskStatus.COMPLETED and task.get(
            "result_ready", "false"
        ) == "true"

    def result_path(self, task_id: str) -> Path:
        return self.work_dir / f"output_{task_id}.pptx"


class TestServerApp(unittest.TestCase):
    """服务端路由测试。"""

    def setUp(self) -> None:
        self.work_dir = Path(tempfile.mkdtemp())
        self.fake_manager = FakeTaskManager(self.work_dir)
        self.test_config = ServerConfig(
            redis_host="localhost",
            redis_port=6379,
            work_dir=self.work_dir,
            max_upload_bytes=100 * 1024 * 1024,
        )
        # 伪 Redis：ping 默认成功
        self.fake_redis = MagicMock()
        self.fake_redis.ping = AsyncMock(return_value=True)

        app.dependency_overrides[get_config] = lambda: self.test_config
        app.dependency_overrides[get_manager] = lambda: self.fake_manager
        app.dependency_overrides[get_redis_dep] = lambda: self.fake_redis

        # lifespan 启动时会 ping（模块级），patch 为成功以放行 fail-fast
        self._ping_patch = patch(
            "ppt_speech.server.redis_client.ping",
            new=AsyncMock(return_value=True),
        )
        self._ping_patch.start()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self._ping_patch.stop()
        import shutil

        if self.work_dir.exists():
            shutil.rmtree(self.work_dir, ignore_errors=True)

    def _client(self) -> TestClient:
        return TestClient(app)

    # ------------------------------------------------------------------
    # 健康检查
    # ------------------------------------------------------------------

    def test_health_ok(self) -> None:
        with self._client() as client:
            resp = client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["redis"])

    def test_health_degraded(self) -> None:
        self.fake_redis.ping = AsyncMock(side_effect=Exception("down"))
        with self._client() as client:
            resp = client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 503)
        self.assertFalse(resp.json()["redis"])

    # ------------------------------------------------------------------
    # 创建任务
    # ------------------------------------------------------------------

    def test_create_task_success(self) -> None:
        with self._client() as client:
            resp = client.post(
                "/api/v1/tasks",
                files={"file": ("input.pptx", b"pptx bytes", _PPTX_MEDIA)},
                data={
                    "voice_name": "zh-CN-XiaoxiaoNeural",
                    "speech_rate": "+0%",
                    "auto_advance": "true",
                    "auto_advance_delay": "2.0",
                },
            )
        self.assertEqual(resp.status_code, 202)
        body = resp.json()
        self.assertIn("task_id", body)
        self.assertEqual(body["status"], TaskStatus.PENDING)
        self.assertTrue(body["progress_url"].endswith("/progress"))
        self.assertTrue(body["result_url"].endswith("/result"))

    def test_create_missing_file(self) -> None:
        with self._client() as client:
            resp = client.post("/api/v1/tasks", data={"voice_name": "zh-CN-XiaoxiaoNeural"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "missing_file")

    def test_create_invalid_file_type(self) -> None:
        with self._client() as client:
            resp = client.post(
                "/api/v1/tasks",
                files={"file": ("notes.txt", b"hello", "text/plain")},
                data={"voice_name": "zh-CN-XiaoxiaoNeural"},
            )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["code"], "invalid_file_type")

    def test_create_invalid_voice(self) -> None:
        with self._client() as client:
            resp = client.post(
                "/api/v1/tasks",
                files={"file": ("input.pptx", b"pptx", _PPTX_MEDIA)},
                data={"voice_name": "bad-voice"},
            )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["code"], "invalid_config")

    def test_create_invalid_delay(self) -> None:
        with self._client() as client:
            resp = client.post(
                "/api/v1/tasks",
                files={"file": ("input.pptx", b"pptx", _PPTX_MEDIA)},
                data={"auto_advance_delay": "not-a-number"},
            )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["code"], "invalid_config")

    def test_create_too_large(self) -> None:
        # 临时调小上限
        small_config = ServerConfig(
            redis_host="localhost",
            redis_port=6379,
            work_dir=self.work_dir,
            max_upload_bytes=10,
        )
        app.dependency_overrides[get_config] = lambda: small_config
        with self._client() as client:
            resp = client.post(
                "/api/v1/tasks",
                files={"file": ("input.pptx", b"x" * 100, _PPTX_MEDIA)},
                data={"voice_name": "zh-CN-XiaoxiaoNeural"},
            )
        self.assertEqual(resp.status_code, 413)
        self.assertEqual(resp.json()["code"], "too_large")

    # ------------------------------------------------------------------
    # voices 列表
    # ------------------------------------------------------------------

    def test_list_voices_success(self) -> None:
        voices = [
            {"Name": "Voice A", "Locale": "en-US", "Gender": "Female"},
            {"Name": "Voice B", "Locale": "zh-CN", "Gender": "Male"},
        ]
        with patch(
            "ppt_speech.tts_client.get_voices_list",
            new=AsyncMock(return_value=voices),
        ):
            with self._client() as client:
                resp = client.get("/api/v1/voices")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("voices", body)
        self.assertEqual(body["voices"], voices)

    def test_list_voices_tts_error(self) -> None:
        from edge_tts.exceptions import EdgeTTSException

        with patch(
            "ppt_speech.tts_client.get_voices_list",
            new=AsyncMock(side_effect=EdgeTTSException("boom")),
        ):
            with self._client() as client:
                resp = client.get("/api/v1/voices")
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()["code"], "tts_unavailable")

    def test_list_voices_unexpected_error(self) -> None:
        with patch(
            "ppt_speech.tts_client.get_voices_list",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            with self._client() as client:
                resp = client.get("/api/v1/voices")
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json()["code"], "voices_failed")

    # ------------------------------------------------------------------
    # 查询任务
    # ------------------------------------------------------------------

    def test_get_task_found(self) -> None:
        self.fake_manager.tasks["t-1"] = {
            "task_id": "t-1",
            "status": TaskStatus.PROCESSING,
            "percent": "50.0",
        }
        with self._client() as client:
            resp = client.get("/api/v1/tasks/t-1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], TaskStatus.PROCESSING)

    def test_get_task_not_found(self) -> None:
        with self._client() as client:
            resp = client.get("/api/v1/tasks/nope")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["code"], "not_found")

    def test_list_tasks(self) -> None:
        self.fake_manager.tasks["t-1"] = {"task_id": "t-1", "status": TaskStatus.COMPLETED}
        with self._client() as client:
            resp = client.get("/api/v1/tasks")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["tasks"]), 1)

    # ------------------------------------------------------------------
    # 下载结果
    # ------------------------------------------------------------------

    def test_result_not_ready(self) -> None:
        self.fake_manager.tasks["t-1"] = {
            "task_id": "t-1",
            "status": TaskStatus.PROCESSING,
            "result_ready": "false",
        }
        with self._client() as client:
            resp = client.get("/api/v1/tasks/t-1/result")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["code"], "not_ready")

    def test_result_failed(self) -> None:
        self.fake_manager.tasks["t-1"] = {
            "task_id": "t-1",
            "status": TaskStatus.FAILED,
            "error": "boom",
            "result_ready": "false",
        }
        with self._client() as client:
            resp = client.get("/api/v1/tasks/t-1/result")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["code"], "failed")

    def test_result_ready(self) -> None:
        self.fake_manager.tasks["t-1"] = {
            "task_id": "t-1",
            "status": TaskStatus.COMPLETED,
            "result_ready": "true",
        }
        # 写入真实输出文件
        out = self.fake_manager.result_path("t-1")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"output pptx bytes")
        with self._client() as client:
            resp = client.get("/api/v1/tasks/t-1/result")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b"output pptx bytes")

    def test_result_expired(self) -> None:
        self.fake_manager.tasks["t-1"] = {
            "task_id": "t-1",
            "status": TaskStatus.COMPLETED,
            "result_ready": "true",
        }
        # 不写输出文件 → 视为过期清理
        with self._client() as client:
            resp = client.get("/api/v1/tasks/t-1/result")
        self.assertEqual(resp.status_code, 410)
        self.assertEqual(resp.json()["code"], "expired")


if __name__ == "__main__":
    unittest.main()
