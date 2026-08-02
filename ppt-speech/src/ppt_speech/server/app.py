"""FastAPI 服务端应用与路由定义。

暴露 ppt-speech 处理服务的 HTTP API：

- ``POST /api/v1/tasks``：上传 pptx + 配置参数，创建后台处理任务。
- ``GET /api/v1/tasks/{task_id}/progress``：SSE 实时进度流。
- ``GET /api/v1/tasks/{task_id}``：任务状态 JSON。
- ``GET /api/v1/tasks/{task_id}/result``：下载处理结果 pptx。
- ``GET /api/v1/health``：健康检查（含 Redis 连通性）。

生命周期（lifespan）启动时校验 Redis 可用（fail-fast），构建
:class:`TaskManager` 并启动磁盘清理协程；关闭时取消清理协程并释放 Redis。
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from redis.asyncio import Redis

from ppt_speech.server import redis_client
from ppt_speech.server.cleanup import cleanup_loop
from ppt_speech.server.config import ServerConfig
from ppt_speech.server.progress import TaskStatus
from ppt_speech.server.sse import event_stream
from ppt_speech.server.tasks import TaskManager

# PPTX MIME 类型
_PPTX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)

# 模块级单例（由 lifespan 初始化），供依赖注入函数返回。
_config: Optional[ServerConfig] = None
_manager: Optional[TaskManager] = None
_cleanup_task: Optional[asyncio.Task] = None


# ---------------------------------------------------------------------------
# 依赖注入
# ---------------------------------------------------------------------------


def get_config() -> ServerConfig:
    """返回服务端配置单例（供测试 override）。"""
    if _config is None:
        return ServerConfig.from_env()
    return _config


def get_redis_dep() -> Redis:
    """返回 Redis 客户端单例（供测试 override）。"""
    return redis_client.get_redis()


def get_manager() -> TaskManager:
    """返回 TaskManager 单例（供测试 override）。"""
    if _manager is None:
        return TaskManager(get_redis_dep(), get_config())
    return _manager


# ---------------------------------------------------------------------------
# 生命周期
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用启动/关闭钩子：校验 Redis、构建管理器、起清理协程。"""
    global _config, _manager, _cleanup_task

    _config = ServerConfig.from_env()
    redis_client.configure(_config)
    redis_client.set_client(None)  # 重置，确保按新配置创建

    redis = redis_client.get_redis()
    if not await redis_client.ping():
        await redis_client.close()
        raise RuntimeError(
            f"无法连接 Redis {_config.redis_host}:{_config.redis_port}，服务拒绝启动"
        )

    _manager = TaskManager(redis, _config)
    _cleanup_task = asyncio.create_task(cleanup_loop(_config))

    try:
        yield
    finally:
        if _cleanup_task is not None:
            _cleanup_task.cancel()
            try:
                await _cleanup_task
            except (asyncio.CancelledError, Exception):
                pass
        await redis_client.close()


app = FastAPI(
    title="ppt-speech-server",
    description="将 PowerPoint 备注自动转为语音并嵌入演示文稿的 HTTP 服务",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# 错误响应辅助
# ---------------------------------------------------------------------------


def _error(status_code: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "detail": detail},
    )


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------


@app.get("/api/v1/health", response_model=None)
async def health(redis: Redis = Depends(get_redis_dep)) -> JSONResponse:
    """健康检查：返回服务与 Redis 连通状态。"""
    try:
        redis_ok = bool(await redis.ping())
    except Exception:
        redis_ok = False
    if redis_ok:
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "redis": True, "version": "0.1.0"},
        )
    return JSONResponse(
        status_code=503,
        content={"status": "degraded", "redis": False, "version": "0.1.0"},
    )


@app.get("/api/v1/voices", response_model=None)
async def list_voices() -> JSONResponse:
    """获取 Edge TTS 可用语音列表。"""
    from edge_tts.exceptions import EdgeTTSException

    from ppt_speech.tts_client import get_voices_list

    try:
        voices = await get_voices_list()
    except EdgeTTSException as exc:
        return _error(502, "tts_unavailable", str(exc))
    except Exception as exc:
        return _error(500, "voices_failed", str(exc))

    return JSONResponse(status_code=200, content={"voices": voices})


@app.post("/api/v1/tasks", response_model=None)
async def create_task(
    file: Optional[UploadFile] = File(None),
    voice_name: str = Form("zh-CN-XiaoxiaoNeural"),
    speech_rate: str = Form("+0%"),
    auto_advance: str = Form("true"),
    auto_advance_delay: str = Form("2.0"),
    manager: TaskManager = Depends(get_manager),
    config: ServerConfig = Depends(get_config),
) -> JSONResponse:
    """上传 pptx 并创建后台处理任务。

    请求为 ``multipart/form-data``，字段：``file``（必填）、``voice_name``、
    ``speech_rate``、``auto_advance``、``auto_advance_delay``。
    """
    # 文件存在性校验
    if file is None or not file.filename:
        return _error(400, "missing_file", "未上传文件")

    # 扩展名校验
    if not file.filename.lower().endswith(".pptx"):
        return _error(422, "invalid_file_type", "仅支持 .pptx 文件")

    # 读取内容并校验大小
    file_bytes = await file.read()
    if not file_bytes:
        return _error(400, "missing_file", "上传文件为空")
    if len(file_bytes) > config.max_upload_bytes:
        return _error(413, "too_large", "上传文件超过大小限制")

    # 解析布尔/浮点参数
    try:
        auto_advance_bool = auto_advance.strip().lower() in ("true", "1", "yes", "on")
    except (AttributeError, ValueError):
        auto_advance_bool = True
    try:
        auto_advance_delay_float = float(auto_advance_delay)
    except (TypeError, ValueError):
        return _error(422, "invalid_config", "auto_advance_delay 必须为数字")

    params = {
        "voice_name": voice_name,
        "speech_rate": speech_rate,
        "auto_advance": auto_advance_bool,
        "auto_advance_delay": auto_advance_delay_float,
    }

    # 创建任务（内部校验 voice/speech_rate 格式，失败抛 ValueError）
    try:
        task_id = await manager.create_task(file_bytes, file.filename, params)
    except ValueError as exc:
        return _error(422, "invalid_config", str(exc))
    except OSError as exc:
        return _error(500, "create_failed", str(exc))

    return JSONResponse(
        status_code=202,
        content={
            "task_id": task_id,
            "status": TaskStatus.PENDING,
            "progress_url": f"/api/v1/tasks/{task_id}/progress",
            "result_url": f"/api/v1/tasks/{task_id}/result",
        },
    )


@app.get("/api/v1/tasks/{task_id}", response_model=None)
async def get_task(
    task_id: str,
    manager: TaskManager = Depends(get_manager),
) -> JSONResponse:
    """查询任务状态。"""
    task = await manager.get_task(task_id)
    if not task:
        return _error(404, "not_found", f"任务不存在: {task_id}")
    return JSONResponse(status_code=200, content=task)


@app.get("/api/v1/tasks/{task_id}/progress", response_model=None)
async def task_progress(
    task_id: str,
    redis: Redis = Depends(get_redis_dep),
    config: ServerConfig = Depends(get_config),
):
    """SSE 实时进度流。"""
    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        event_stream(task_id, redis, heartbeat_seconds=config.sse_heartbeat_seconds),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲，保障 SSE 实时性
            "Connection": "keep-alive",
        },
    )


@app.get("/api/v1/tasks/{task_id}/result", response_model=None)
async def task_result(
    task_id: str,
    manager: TaskManager = Depends(get_manager),
) -> JSONResponse | FileResponse:
    """下载处理结果 pptx。"""
    task = await manager.get_task(task_id)
    if not task:
        return _error(404, "not_found", f"任务不存在: {task_id}")

    status = task.get("status", "")
    if status == TaskStatus.FAILED:
        return _error(404, "failed", task.get("error", "任务处理失败"))
    if not manager.is_result_ready(task):
        return _error(409, "not_ready", f"任务尚未完成，当前状态: {status}")

    result_file = manager.result_path(task_id)
    if not result_file.exists():
        return _error(410, "expired", "结果文件已过期被清理")

    return FileResponse(
        path=str(result_file),
        media_type=_PPTX_MEDIA_TYPE,
        filename=f"output_{task_id[:8]}.pptx",
    )


@app.get("/api/v1/tasks", response_model=None)
async def list_tasks(
    manager: TaskManager = Depends(get_manager),
) -> JSONResponse:
    """列出所有任务状态。"""
    tasks = await manager.list_tasks()
    return JSONResponse(status_code=200, content={"tasks": tasks})
