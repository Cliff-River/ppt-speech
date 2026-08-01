"""服务端配置模块。

从环境变量读取 ppt-speech 服务端的运行参数，包括 Redis 连接信息、
监听地址、工作目录、上传限制与结果保留时长等。

所有配置均可通过环境变量覆盖，便于容器化部署与本地调试。
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


def _default_work_dir() -> Path:
    """默认工作目录：系统临时目录下的 ppt_speech_server 子目录。"""
    return Path(tempfile.gettempdir()) / "ppt_speech_server"


@dataclass(slots=True)
class ServerConfig:
    """ppt-speech 服务端运行配置。

    Attributes:
        redis_host: Redis 服务器地址。
        redis_port: Redis 端口。
        redis_db: Redis 数据库编号。
        host: 服务监听地址。
        port: 服务监听端口。
        work_dir: 任务工作目录，存放上传的输入文件与生成的输出文件
            （按 task_id 分子目录）。
        max_upload_bytes: 单次上传文件大小上限（字节）。
        result_ttl_seconds: 任务终态后结果保留时长（秒）；超过后清理磁盘
            文件与 Redis 任务键。
        sse_heartbeat_seconds: SSE 心跳间隔（秒）。
        cleanup_interval_seconds: 磁盘清理协程扫描间隔（秒）。
    """

    redis_host: str = "192.168.79.160"
    redis_port: int = 6379
    redis_db: int = 0
    host: str = "0.0.0.0"
    port: int = 8000
    work_dir: Path = field(default_factory=_default_work_dir)
    max_upload_bytes: int = 100 * 1024 * 1024
    result_ttl_seconds: int = 3600
    sse_heartbeat_seconds: int = 15
    cleanup_interval_seconds: int = 300

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """从环境变量构建配置，未设置的项沿用默认值。

        注意：本类使用 ``slots=True``，类属性为 slot 描述符而非默认值，
        故此处以字面量给出默认值（与字段声明保持一致）。
        """
        work_dir = os.environ.get("WORK_DIR")
        max_upload_mb = os.environ.get("MAX_UPLOAD_MB")

        return cls(
            redis_host=os.environ.get("REDIS_HOST", "192.168.79.160"),
            redis_port=int(os.environ.get("REDIS_PORT", "6379")),
            redis_db=int(os.environ.get("REDIS_DB", "0")),
            host=os.environ.get("HOST", "0.0.0.0"),
            port=int(os.environ.get("PORT", "8000")),
            work_dir=Path(work_dir) if work_dir else _default_work_dir(),
            max_upload_bytes=(
                int(max_upload_mb) * 1024 * 1024 if max_upload_mb else 100 * 1024 * 1024
            ),
            result_ttl_seconds=int(os.environ.get("RESULT_TTL_SECONDS", "3600")),
            sse_heartbeat_seconds=int(os.environ.get("SSE_HEARTBEAT_SECONDS", "15")),
            cleanup_interval_seconds=int(
                os.environ.get("CLEANUP_INTERVAL_SECONDS", "300")
            ),
        )
