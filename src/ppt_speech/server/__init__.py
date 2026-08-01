"""ppt-speech 服务端子包。

提供基于 FastAPI 的 HTTP 服务，将核心 ``ppt_speech`` 库包装为客户端-服务端
架构：客户端上传 pptx，服务端后台处理并经 SSE 实时回传进度，处理完成后
返回带配音的结果文件。Redis 用于任务/进度状态存储与 pub/sub 事件广播。

公共接口
--------
- :data:`app`：FastAPI 应用实例，供 uvicorn 加载。
- :func:`main`：控制台入口，启动 uvicorn 服务。

依赖
====
服务端依赖（``fastapi``、``uvicorn``、``redis``、``python-multipart``）声明于
``pyproject.toml`` 的 ``[project.optional-dependencies] server`` 组，需通过
``uv pip install -e ".[server]"`` 单独安装，核心库不受影响。
"""

from __future__ import annotations


def main() -> None:
    """控制台入口：启动 ppt-speech HTTP 服务。

    供 ``pyproject.toml`` 中声明的 ``ppt-speech-server`` 控制台脚本调用
    （``ppt-speech-server = "ppt_speech.server:main"``），亦可经由
    ``python -m ppt_speech.server``（见 :mod:`ppt_speech.server.__main__`）触发。

    监听地址与端口由环境变量 ``HOST`` / ``PORT`` 控制（默认 0.0.0.0:8000）。
    """
    import uvicorn

    from ppt_speech.server.app import app
    from ppt_speech.server.config import ServerConfig

    config = ServerConfig.from_env()
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level="info",
    )


__all__ = ["main"]
