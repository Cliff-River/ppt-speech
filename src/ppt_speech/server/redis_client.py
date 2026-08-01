"""Redis 客户端模块。

封装 :mod:`redis.asyncio` 的连接管理、健康检查与任务/事件键命名约定。

Redis 在本服务中仅承担**任务与进度状态存储**以及 **pub/sub 实时事件广播**
两类职责：

- ``ppt_speech:task:{task_id}``（Hash）：任务元数据与最新进度快照。
- ``ppt_speech:events:{task_id}``（Pub/Sub 频道）：实时进度事件 JSON。
- ``ppt_speech:tasks:index``（Set）：全部 task_id，供列表查询。

**不缓存** TTS 音频字节或最终 pptx 文件——这些大文件存于磁盘
（``work_dir/{task_id}/``），由 :mod:`ppt_speech.server.cleanup` 周期清理。
"""

from __future__ import annotations

from typing import Optional

from redis.asyncio import Redis

from ppt_speech.server.config import ServerConfig

# Redis key 前缀与片段
_KEY_PREFIX = "ppt_speech"
_TASK_PREFIX = f"{_KEY_PREFIX}:task"
_EVENTS_PREFIX = f"{_KEY_PREFIX}:events"
_INDEX_KEY = f"{_KEY_PREFIX}:tasks:index"

# 模块级单例；测试可通过 configure 注入 fakeredis。
_redis: Optional[Redis] = None
_config: Optional[ServerConfig] = None


def configure(config: ServerConfig) -> None:
    """设置全局配置，下次 :func:`get_redis` 调用时据此创建连接。"""
    global _config
    _config = config


def set_client(client: Optional[Redis]) -> None:
    """注入一个已存在的 Redis 客户端（主要用于测试注入 fakeredis）。

    传入 None 则清除单例，下次 :func:`get_redis` 重新创建。
    """
    global _redis
    _redis = client


def get_redis() -> Redis:
    """返回全局 Redis 客户端单例；不存在时按当前配置惰性创建。"""
    global _redis
    if _redis is not None:
        return _redis

    if _config is None:
        configure(ServerConfig.from_env())

    assert _config is not None  # 仅供类型检查器 narrowing
    _redis = Redis(
        host=_config.redis_host,
        port=_config.redis_port,
        db=_config.redis_db,
        decode_responses=True,
    )
    return _redis


async def ping() -> bool:
    """检查 Redis 连接是否可用，返回 PING 是否成功。"""
    try:
        return bool(await get_redis().ping())
    except Exception:
        return False


async def close() -> None:
    """关闭并清除全局 Redis 客户端单例。"""
    global _redis
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception:
            pass
        _redis = None


# ---------------------------------------------------------------------------
# 键命名约定
# ---------------------------------------------------------------------------


def task_key(task_id: str) -> str:
    """任务状态 Hash 的键名：``ppt_speech:task:{task_id}``。"""
    return f"{_TASK_PREFIX}:{task_id}"


def events_channel(task_id: str) -> str:
    """任务实时事件 pub/sub 频道名：``ppt_speech:events:{task_id}``。"""
    return f"{_EVENTS_PREFIX}:{task_id}"


def task_index_key() -> str:
    """全局任务索引 Set 的键名：``ppt_speech:tasks:index``。"""
    return _INDEX_KEY
