"""任务管理模块。

负责任务的完整生命周期：创建（落盘上传文件 + 写 Redis 初始状态）、
后台处理（调用核心 :func:`ppt_speech.pipeline.process_slides`）、
状态查询与列表。处理在独立的 asyncio 任务中运行，进度经
:class:`ppt_speech.server.progress.ProgressReporter` 实时写入 Redis 并广播。

任务文件存放于 ``work_dir/{task_id}/``：
- ``input.pptx``：上传的原始文件（处理完成后删除）。
- ``output.pptx``：生成的带配音演示文稿（保留供下载，由清理协程过期删除）。
"""

from __future__ import annotations

import asyncio
import traceback
import uuid
from pathlib import Path
from typing import Any, Optional

from pptx import Presentation
from redis.asyncio import Redis

from ppt_speech.config import PTSpeechConfig
from ppt_speech.pipeline import process_slides
from ppt_speech.server import redis_client
from ppt_speech.server.config import ServerConfig
from ppt_speech.server.progress import (
    ProgressReporter,
    Stage,
    TaskStatus,
    set_terminal_state,
)

# 输入/输出文件名固定
_INPUT_FILENAME = "input.pptx"
_OUTPUT_FILENAME = "output.pptx"


class TaskManager:
    """任务生命周期管理器。

    Args:
        redis: Redis 客户端（可为 fakeredis）。
        config: 服务端配置（取 work_dir 与 result_ttl_seconds）。
    """

    def __init__(self, redis: Redis, config: ServerConfig) -> None:
        self._redis = redis
        self._config = config
        # 持有后台任务引用，避免被 GC 回收。
        self._background_tasks: set[asyncio.Task] = set()

    # ------------------------------------------------------------------
    # 路径辅助
    # ------------------------------------------------------------------

    def task_dir(self, task_id: str) -> Path:
        """任务工作子目录：``work_dir/{task_id}``。"""
        return self._config.work_dir / task_id

    def result_path(self, task_id: str) -> Path:
        """结果文件路径：``work_dir/{task_id}/output.pptx``。"""
        return self.task_dir(task_id) / _OUTPUT_FILENAME

    # ------------------------------------------------------------------
    # 创建任务
    # ------------------------------------------------------------------

    async def create_task(
        self,
        file_bytes: bytes,
        filename: str,
        params: dict[str, Any],
    ) -> str:
        """创建并启动一个处理任务。

        流程：生成 task_id → 落盘输入文件 → 构建并校验配置（失败则清理
        并抛 ``ValueError``）→ 写 PENDING 状态 → 启动后台处理 → 返回 task_id。

        Args:
            file_bytes: 上传的 pptx 文件二进制内容。
            filename: 原始文件名（仅用于展示）。
            params: 配置参数（voice_name / speech_rate / auto_advance /
                auto_advance_delay）。

        Returns:
            新任务的 task_id。

        Raises:
            ValueError: 当 voice_name / speech_rate 等参数非法时（供 API 层
                转为 422）。
            OSError: 当文件落盘失败时。
        """
        task_id = str(uuid.uuid4())
        task_dir = self.task_dir(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)

        input_path = task_dir / _INPUT_FILENAME
        try:
            input_path.write_bytes(file_bytes)
        except OSError as exc:
            # 落盘失败：清理已创建的目录并向上抛出。
            self._remove_dir(task_dir)
            raise OSError(f"无法保存上传文件: {exc}") from exc

        config = self._build_config(task_dir, params)
        # 校验在落盘之后进行：voice/rate 格式错误抛 ValueError，文件已存在
        # 故不会误判 FileNotFoundError。校验失败时清理目录并抛出，供 API 层
        # 返回 422，且不向 Redis 注册任何任务。
        try:
            config.validate()
        except (ValueError, FileNotFoundError) as exc:
            self._remove_dir(task_dir)
            raise ValueError(str(exc)) from exc

        # 写入 PENDING 初始状态。
        await self._redis.hset(
            redis_client.task_key(task_id),
            mapping={
                "task_id": task_id,
                "status": TaskStatus.PENDING,
                "stage": Stage.VALIDATING,
                "slide_idx": "0",
                "total_slides": "0",
                "percent": "0.0",
                "eta_seconds": "",
                "message": "任务已创建，等待处理",
                "input_filename": filename,
                "created_at": str(asyncio.get_event_loop().time()),
                "updated_at": str(asyncio.get_event_loop().time()),
                "error": "",
                "result_ready": "false",
            },
        )
        await self._redis.sadd(redis_client.task_index_key(), task_id)

        # 启动后台处理。
        task = asyncio.create_task(self.run_task(task_id, config, filename))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        return task_id

    def _build_config(
        self, task_dir: Path, params: dict[str, Any]
    ) -> PTSpeechConfig:
        """根据任务子目录与参数构建 PTSpeechConfig。"""
        return PTSpeechConfig(
            input_dir=task_dir,
            output_dir=task_dir,
            input_filename=_INPUT_FILENAME,
            output_filename=_OUTPUT_FILENAME,
            voice_name=params.get("voice_name", "zh-CN-XiaoxiaoNeural"),
            speech_rate=params.get("speech_rate", "+0%"),
            auto_advance=bool(params.get("auto_advance", True)),
            auto_advance_delay=float(params.get("auto_advance_delay", 2.0)),
        )

    # ------------------------------------------------------------------
    # 后台处理
    # ------------------------------------------------------------------

    async def run_task(
        self,
        task_id: str,
        config: PTSpeechConfig,
        input_filename: str,
    ) -> None:
        """执行单个任务的后台处理（在独立 asyncio 任务中运行）。

        成功 → 置 COMPLETED（result_ready=True）；异常 → 置 FAILED 并记录
        堆栈。无论成败，finally 中删除输入文件（保留输出供下载）。
        """
        key = redis_client.task_key(task_id)
        # 显式置 PROCESSING，确保 SSE 在首个事件前即见处理中状态。
        await self._redis.hset(key, mapping={"status": TaskStatus.PROCESSING})

        try:
            prs = Presentation(str(config.input_path))
            total = len(prs.slides)
            reporter = ProgressReporter(task_id, self._redis, total, input_filename)
            await process_slides(prs, config, on_progress=reporter)

            await set_terminal_state(
                task_id,
                self._redis,
                TaskStatus.COMPLETED,
                stage=Stage.COMPLETED,
                message="处理完成，结果可下载",
                result_ready=True,
                ttl_seconds=self._config.result_ttl_seconds,
                total_slides=total,
                input_filename=input_filename,
            )
        except Exception as exc:  # noqa: BLE001 — 后台任务需捕获所有异常
            await set_terminal_state(
                task_id,
                self._redis,
                TaskStatus.FAILED,
                stage=Stage.FAILED,
                message=f"处理失败: {exc}",
                error=traceback.format_exc(),
                result_ready=False,
                ttl_seconds=self._config.result_ttl_seconds,
                input_filename=input_filename,
            )
        finally:
            # 删除输入文件，保留输出供下载。
            input_file = config.input_path
            if input_file.exists():
                try:
                    input_file.unlink()
                except OSError:
                    pass

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def get_task(self, task_id: str) -> Optional[dict[str, str]]:
        """获取任务状态快照（HGETALL）；不存在返回 None。"""
        data = await self._redis.hgetall(redis_client.task_key(task_id))
        return data if data else None

    async def list_tasks(self) -> list[dict[str, str]]:
        """列出所有任务的状态快照。"""
        task_ids = await self._redis.smembers(redis_client.task_index_key())
        tasks: list[dict[str, str]] = []
        for task_id in task_ids:
            data = await self.get_task(task_id)
            if data:
                tasks.append(data)
        return tasks

    def is_result_ready(self, task: dict[str, str]) -> bool:
        """根据任务快照判断结果文件是否可下载。"""
        return task.get("status") == TaskStatus.COMPLETED and task.get(
            "result_ready", "false"
        ).lower() == "true"

    # ------------------------------------------------------------------
    # 清理辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _remove_dir(path: Path) -> None:
        """静默删除目录树。"""
        if path.exists():
            try:
                import shutil

                shutil.rmtree(path, ignore_errors=True)
            except OSError:
                pass
